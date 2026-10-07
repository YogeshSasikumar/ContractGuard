import requests
import json

with open("test_contract.pdf", "rb") as f:
    files = {"file": ("test_contract.pdf", f, "application/pdf")}
    resp = requests.post("http://localhost:8000/api/upload", files=files, timeout=120)

if resp.status_code == 200:
    data = resp.json()
    print("=== ANALYSIS RESULT ===")
    print("Document:", data["document_name"])
    print("Pages:", data["total_pages"])
    print("Processing Time:", data["processing_time"], "s")
    print("Overall Risk Score:", data["risk_summary"]["overall_risk_score"])
    print("HIGH:", data["risk_summary"]["high_risk"], " MEDIUM:", data["risk_summary"]["medium_risk"], " LOW:", data["risk_summary"]["low_risk"])
    print()
    for clause in data["clauses"]:
        print("  [%s] %s" % (clause["risk_level"], clause["clause_type"]))
        print("    Confidence:", clause["confidence"], " Model:", clause.get("model_used", "N/A"))
        print("    Centrality:", clause.get("centrality", "N/A"), " Risk Score:", clause.get("risk_score", "N/A"))
        print("    Text:", clause["text"][:100], "...")
        print()
else:
    print("ERROR:", resp.status_code)
    print(resp.text)
