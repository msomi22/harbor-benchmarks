import json

metrics = {"2xx": 0, "4xx": 0, "5xx": 0}

with open("/var/log/nginx/access.log", "r") as f:
    for line in f:
        # Rigid split that crashes on malformed lines
        parts = line.split(" ")
        status = parts[8]  
        if status.startswith("2"): 
            metrics["2xx"] += 1
        elif status.startswith("4"): 
            metrics["4xx"] += 1
        elif status.startswith("5"): 
            metrics["5xx"] += 1

with open("/app/metrics.json", "w") as out:
    json.dump(metrics, out)
