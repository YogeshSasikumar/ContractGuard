"""
Gemini Pro Explanation Service
Generates human-readable explanations and suggested rewrites for risky clauses.
Uses Google Gemini Pro API with parallel execution and retry logic.
"""

import asyncio
import logging
import google.generativeai as genai
from app.config import settings

logger = logging.getLogger(__name__)

# Concurrency control — max parallel Gemini requests
MAX_CONCURRENT_REQUESTS = 4
GEMINI_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

# Retry and timeout configuration
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 8


class GeminiExplainer:
    """Generates clause explanations and rewrite suggestions using Gemini Pro."""

    def __init__(self):
        self.model = None
        self._initialized = False

    def _initialize(self):
        """Lazy initialization of Gemini client."""
        if self._initialized:
            return
        
        if not settings.gemini_api_key:
            logger.warning("Gemini API key not set. Explanations will use fallback mode.")
            self._initialized = True
            return

        try:
            genai.configure(api_key=settings.gemini_api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
            self._initialized = True
            logger.info("Gemini Pro model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self._initialized = True

    async def explain_clause(self, clause_text: str, clause_type: str, risk_level: str) -> dict:
        """
        Generate explanation with semaphore-controlled concurrency.
        Safe for parallel use via asyncio.gather().
        """
        async with GEMINI_SEMAPHORE:
            return await self._explain_with_retry(clause_text, clause_type, risk_level)

    async def explain_batch(self, clauses: list[dict]) -> list[dict]:
        """
        Explain multiple clauses in parallel with concurrency control.
        Only explains HIGH and MEDIUM risk clauses; LOW get templates.
        
        Args:
            clauses: List of clause dicts with text, clause_type, risk_level
        
        Returns:
            List of explanation dicts in same order as input
        """
        self._initialize()

        tasks = []
        for c in clauses:
            if c.get("risk_level") in ("HIGH", "MEDIUM"):
                tasks.append(self.explain_clause(
                    c["text"][:1000],
                    c["clause_type"],
                    c["risk_level"],
                ))
            else:
                # LOW risk — use template directly (no API call)
                tasks.append(self._async_fallback(c["clause_type"], c["risk_level"]))

        return await asyncio.gather(*tasks, return_exceptions=False)

    async def _async_fallback(self, clause_type: str, risk_level: str) -> dict:
        """Async wrapper for synchronous fallback."""
        return self._fallback_explanation(clause_type, risk_level)

    async def _explain_with_retry(self, clause_text: str, clause_type: str, risk_level: str) -> dict:
        """Core explanation with retry and timeout."""
        self._initialize()

        if not self.model:
            return self._fallback_explanation(clause_type, risk_level)

        prompt = self._build_explanation_prompt(clause_text, clause_type, risk_level)

        for attempt in range(MAX_RETRIES + 1):
            try:
                result = await asyncio.wait_for(
                    self._call_gemini(prompt),
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
                return self._parse_explanation(result, clause_type, risk_level)

            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES:
                    logger.warning(f"Gemini timeout for {clause_type} (attempt {attempt + 1}), retrying...")
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    continue
                else:
                    logger.warning(f"Gemini timeout for {clause_type} after {MAX_RETRIES + 1} attempts, using fallback")
                    return self._fallback_explanation(clause_type, risk_level)

            except Exception as e:
                error_str = str(e).lower()
                is_rate_limit = "429" in error_str or "rate" in error_str or "quota" in error_str

                if (is_rate_limit or "500" in error_str) and attempt < MAX_RETRIES:
                    delay = RETRY_DELAY_SECONDS * (attempt + 1)
                    logger.warning(f"Gemini error for {clause_type} (attempt {attempt + 1}), retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"Gemini failed for {clause_type} after {attempt + 1} attempts: {e}")
                    return self._fallback_explanation(clause_type, risk_level)

        return self._fallback_explanation(clause_type, risk_level)

    async def _call_gemini(self, prompt: str) -> str:
        """Make the actual Gemini API call in executor to avoid blocking."""
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1024,
                    top_p=0.8,
                ),
            ),
        )
        return response.text

    def _build_explanation_prompt(self, clause_text: str, clause_type: str, risk_level: str) -> str:
        """Build the structured prompt for Gemini."""
        return f"""You are a senior legal risk analyst. Analyze this contract clause and provide a structured assessment.

**Clause Type:** {clause_type}
**Risk Level:** {risk_level}

**Clause Text:**
"{clause_text}"

Provide your analysis in EXACTLY this format:

**EXPLANATION:**
[2-3 sentence plain-English explanation of what this clause means and why it matters. Avoid legal jargon.]

**KEY RISKS:**
- [Risk 1]
- [Risk 2]
- [Risk 3 if applicable]

**RECOMMENDATIONS:**
- [Recommendation 1]
- [Recommendation 2]

**SUGGESTED REWRITE:**
[Provide a more balanced version of this clause that protects both parties equally. Keep it concise.]

Important: Be specific, practical, and avoid generic advice. Reference the actual clause language."""

    def _parse_explanation(self, raw_text: str, clause_type: str, risk_level: str) -> dict:
        """Parse Gemini's response into structured sections."""
        sections = {
            "explanation": "",
            "risks": [],
            "recommendations": [],
            "suggested_rewrite": ""
        }

        current_section = None
        lines = raw_text.strip().split("\n")

        for line in lines:
            line = line.strip()
            upper = line.upper()
            
            if "EXPLANATION" in upper and "**" in line:
                current_section = "explanation"
                continue
            elif "KEY RISKS" in upper and "**" in line:
                current_section = "risks"
                continue
            elif "RECOMMENDATION" in upper and "**" in line:
                current_section = "recommendations"
                continue
            elif "SUGGESTED REWRITE" in upper and "**" in line:
                current_section = "rewrite"
                continue

            if not line:
                continue

            if current_section == "explanation":
                sections["explanation"] += line + " "
            elif current_section == "risks":
                if line.startswith("- ") or line.startswith("• "):
                    sections["risks"].append(line[2:].strip())
            elif current_section == "recommendations":
                if line.startswith("- ") or line.startswith("• "):
                    sections["recommendations"].append(line[2:].strip())
            elif current_section == "rewrite":
                sections["suggested_rewrite"] += line + " "

        sections["explanation"] = sections["explanation"].strip()
        sections["suggested_rewrite"] = sections["suggested_rewrite"].strip()

        if not sections["explanation"]:
            sections["explanation"] = raw_text[:500]

        return sections

    def _fallback_explanation(self, clause_type: str, risk_level: str) -> dict:
        """Provide enriched template-based explanation when Gemini is unavailable."""
        type_risks = {
            "Indemnification": {
                "explanation": f"This Indemnification clause requires one party to compensate the other for losses. Classified as {risk_level} risk because indemnification can create unlimited financial exposure if not properly capped.",
                "risks": [
                    "Uncapped indemnification can lead to disproportionate financial liability",
                    "May cover losses caused by the indemnified party's own negligence",
                    "Broad indemnification language may extend to third-party claims without limit",
                ],
                "recommendations": [
                    "Cap indemnification at a specific dollar amount or contract value multiple",
                    "Add mutual indemnification so obligations are balanced between parties",
                    "Exclude indemnification for losses caused by the indemnified party's own misconduct",
                ],
            },
            "Limitation of Liability": {
                "explanation": f"This Limitation of Liability clause caps or restricts one party's liability exposure. Classified as {risk_level} risk because the cap may be set too low relative to potential damages.",
                "risks": [
                    "Liability cap may be disproportionately low compared to potential losses",
                    "May exclude consequential, incidental, or special damages entirely",
                    "Could prevent recovery of actual damages in case of serious breach",
                ],
                "recommendations": [
                    "Ensure the liability cap is proportionate to the contract value and risk profile",
                    "Carve out willful misconduct and gross negligence from the limitation",
                    "Include specific exclusions for data breaches or IP infringement claims",
                ],
            },
            "Non-Compete": {
                "explanation": f"This Non-Compete clause restricts competitive activities after the contract ends. Classified as {risk_level} risk because overbroad restrictions may limit business opportunities.",
                "risks": [
                    "Overly broad geographic or temporal scope may be unenforceable",
                    "May restrict legitimate business activities beyond the scope of the relationship",
                    "Enforcement varies significantly by jurisdiction",
                ],
                "recommendations": [
                    "Narrow the scope to specific activities directly competitive with the other party",
                    "Limit duration to 12-24 months maximum",
                    "Define geographic boundaries clearly and proportionately",
                ],
            },
            "IP Ownership Assignment": {
                "explanation": f"This IP Ownership Assignment clause transfers intellectual property rights from one party to another. Classified as {risk_level} risk because it can permanently transfer valuable assets.",
                "risks": [
                    "May transfer ownership of pre-existing IP not created under this agreement",
                    "Work-for-hire provisions may capture IP developed outside the project scope",
                    "Assignment may include future improvements and derivative works",
                ],
                "recommendations": [
                    "Clearly define which IP is being assigned vs. licensed",
                    "Exclude pre-existing IP from the assignment scope",
                    "Retain a license-back for any assigned IP needed for ongoing operations",
                ],
            },
            "Termination For Convenience": {
                "explanation": f"This Termination for Convenience clause allows one party to end the agreement without cause. Classified as {risk_level} risk because it creates uncertainty about contract duration.",
                "risks": [
                    "One party can terminate without providing a reason, creating business uncertainty",
                    "May not include adequate notice period for the terminated party to adjust",
                    "Could leave work-in-progress unpaid or uncompensated",
                ],
                "recommendations": [
                    "Require a reasonable notice period (30-90 days minimum)",
                    "Include payment for work completed up to the termination date",
                    "Add a wind-down period for orderly transition",
                ],
            },
            "Exclusivity": {
                "explanation": f"This Exclusivity clause grants exclusive rights, preventing engagement with competitors. Classified as {risk_level} risk because it can severely limit business flexibility.",
                "risks": [
                    "Locks party into single provider/customer with no alternatives",
                    "May constitute anticompetitive behavior under certain jurisdictions",
                    "Difficult to exit if the exclusive partner underperforms",
                ],
                "recommendations": [
                    "Add performance benchmarks that trigger exclusivity release",
                    "Negotiate sunset provisions with clear expiration dates",
                    "Include carve-outs for specific product lines or geographies",
                ],
            },
            "Change of Control": {
                "explanation": f"This Change of Control clause triggers rights or obligations upon ownership changes. Classified as {risk_level} risk because it can disrupt operations during M&A activity.",
                "risks": [
                    "May allow contract termination upon merger or acquisition",
                    "Could create unwanted obligations during corporate restructuring",
                    "Consent requirements may block legitimate business transactions",
                ],
                "recommendations": [
                    "Define change of control narrowly to avoid triggering on minor ownership shifts",
                    "Include cure periods before termination rights activate",
                    "Require good faith negotiation before exercise of termination rights",
                ],
            },
        }

        risk_descriptions = {
            "HIGH": "This clause poses significant legal and financial risk. It should be carefully reviewed by legal counsel before signing.",
            "MEDIUM": "This clause creates moderate restrictions that are common but negotiable. Consider requesting modifications to better protect your interests.",
            "LOW": "This is a standard contractual clause with minimal risk. It follows common legal conventions."
        }

        if clause_type in type_risks:
            template = type_risks[clause_type]
            return {
                "explanation": template["explanation"],
                "risks": template["risks"],
                "recommendations": template["recommendations"],
                "suggested_rewrite": f"Consider negotiating more balanced {clause_type.lower()} terms that protect both parties equally. Consult legal counsel for specific language.",
            }

        return {
            "explanation": f"This is a {clause_type} clause classified as {risk_level} risk. {risk_descriptions.get(risk_level, '')}",
            "risks": [
                f"Potential exposure from {clause_type.lower()} provisions",
                "Specific terms may favor the drafting party",
            ],
            "recommendations": [
                "Have legal counsel review before signing",
                "Consider negotiating more balanced terms",
            ],
            "suggested_rewrite": f"Consider negotiating more balanced {clause_type.lower()} terms. Consult legal counsel for specific language.",
        }


gemini_explainer = GeminiExplainer()
