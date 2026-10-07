import requests
import time
import json

# Step 1: Upload (should return immediately with job_id)
files = {"file": ("test_contract.pdf", open("test_contract.pdf", "rb"), "application/pdf")}

t0 = time.time()
r = requests.post("http://localhost:8000/api/upload", files=files, timeout=30)
t_upload = time.time() - t0

print("=== UPLOAD ===")
print("Status:", r.status_code)
print("Upload time:", round(t_upload, 2), "s")
print("Response:", r.json())

job_id = r.json().get("job_id")
if not job_id:
    print("ERROR: No job_id returned!")
    exit(1)

# Step 2: Poll for results
print("\n=== POLLING ===")
poll_count = 0
while True:
    time.sleep(2.5)
    poll_count += 1
    
    sr = requests.get("http://localhost:8000/api/status/%s" % job_id, timeout=10)
    data = sr.json()
    
    status = data.get("status")
    progress = data.get("progress", 0)
    step = data.get("step", "")
    
    print("  Poll %d: status=%s progress=%d%% step=%s" % (poll_count, status, progress, step))
    
    if status == "completed":
        result = data.get("result", {})
        t_total = time.time() - t0
        
        print("\n=== COMPLETED ===")
        print("Total time:", round(t_total, 2), "s")
        print("Backend processing:", result.get("processing_time"), "s")
        
        rs = result.get("risk_summary", {})
        print("Clauses:", rs.get("total_clauses"))
        print("High:", rs.get("high_risk"), "| Medium:", rs.get("medium_risk"), "| Low:", rs.get("low_risk"))
        print("Risk Score:", rs.get("overall_risk_score"))
        print("Top Risky:", len(rs.get("top_risky_clauses", [])))
        
        mh = result.get("model_health", {})
        print("Models:", json.dumps(mh))
        
        clauses = result.get("clauses", [])
        print("\nAll fields present:", all(
            c.get("model_trace") is not None and c.get("risks") is not None
            for c in clauses
        ))
        break
    
    elif status == "failed":
        print("\nFAILED:", data.get("error"))
        break
    
    if poll_count > 60:
        print("\nTIMEOUT: Too many polls")
        break
