from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import pandas as pd
from gurobipy import Model, GRB, quicksum

app = FastAPI()

@app.post("/optimize")
async def optimize(request: Request):
    try:
        data = await request.json()
        hikes = data.get("hikes", [])
        requests = data.get("requests", [])


        if not hikes or not requests:
            return JSONResponse(content={"error": "Missing hikes or requests"}, status_code=400)

        # --- Build hike_df ---
        hike_df = pd.DataFrame(hikes)
        print("✅ Created hike_df")

        # Safe difficulty handling
        difficulty_vals = []
        for val in hike_df["difficulty"]:
            try:
                rounded = round(float(val))
                difficulty_vals.append(int(rounded))
            except:
                difficulty_vals.append(2)
        hike_df["difficulty"] = difficulty_vals

        hike_df["rocky"] = hike_df["description_binary"].apply(lambda x: x.get("rocky", 0) if isinstance(x, dict) else 0)
        hike_df["wet"] = hike_df["description_binary"].apply(lambda x: x.get("wet", 0) if isinstance(x, dict) else 0)
        hike_df["steep"] = hike_df["description_binary"].apply(lambda x: x.get("steep", 0) if isinstance(x, dict) else 0)

        # --- Build request_df ---
        request_df = pd.DataFrame(requests).fillna("")
        reason_col = "For each group, list the type of hike. either easy, medium or, hard and any reasons why. Example: Group 1 wants easy because one of the members is old."

        if reason_col not in request_df.columns:
            return JSONResponse(content={"error": f"Missing required column: '{reason_col}'"}, status_code=400)

        request_df["Desired Difficulty Level"] = request_df[reason_col].apply(infer_difficulty)
        request_df["Reason for Request"] = request_df.apply(extract_reason, axis=1)
        request_df["Total tourists"] = request_df["Total tourists"].apply(get_tourist_count)

        result = build_model(hike_df, request_df)
        return JSONResponse(content=result, status_code=200)

    except Exception as e:
        print("❌ Exception:", str(e))
        return JSONResponse(content={"error": str(e)}, status_code=500)

# --- Utilities ---

def infer_difficulty(text):
    text = str(text).lower()
    if "easy" in text: return 1
    if "medium" in text: return 2
    if "hard" in text: return 3
    return 2

def extract_reason(row):
    combined = " ".join(str(v).lower() for v in row.values)  # ✅ FIXED: no ()
    reasons = []
    if "old" in combined: reasons.append("old")
    if "young" in combined: reasons.append("young")
    if any(t in combined for t in ["sick", "hurt", "asma"]): reasons.append("sick")
    if "fit" in combined: reasons.append("fit")
    if "lazy" in combined: reasons.append("lazy")
    if "family" in combined: reasons.append("family")
    if "mixed" in combined: reasons.append("mixed")
    return ", ".join(set(reasons)) if reasons else "mixed"

def get_tourist_count(value):
    try:
        if isinstance(value, (int, float)): return int(value)
        if isinstance(value, str) and value.strip().isdigit(): return int(value.strip())
        return int(float(value))
    except: return 1

# --- Gurobi Optimization ---

def build_model(hike_df, request_df):
    model = Model("group_assignment")
    model.setParam("OutputFlag", 0)

    groups = request_df.index.tolist()
    hikes = hike_df.index.tolist()

    x = {(g, h): model.addVar(vtype=GRB.BINARY) for g in groups for h in hikes}
    model.update()

    for g in groups:
        model.addConstr(quicksum(x[g, h] for h in hikes) == 1)

    for h in hikes:
        model.addConstr(quicksum(
            int(request_df.at[g, "Total tourists"]) * x[g, h]
            for g in groups
        ) <= 8)

    importance_order = ["sick", "old", "young", "family", "mixed", "lazy", "fit", "experienced"]
    importance_weight = {r: len(importance_order) - i for i, r in enumerate(importance_order)}

    def get_reason_weight(reason_str):
        reasons = [r.strip() for r in str(reason_str).split(",") if r.strip()]
        return max([importance_weight.get(r, 1) for r in reasons]) if reasons else 1

    model.setObjective(
        quicksum(
            (
                2 if int(hike_df.loc[h, "difficulty"]) == int(request_df.loc[g, "Desired Difficulty Level"])
                else 1 if int(hike_df.loc[h, "difficulty"]) < int(request_df.loc[g, "Desired Difficulty Level"])
                else 0
            ) * get_reason_weight(request_df.loc[g, "Reason for Request"]) * x[g, h]
            for g in groups for h in hikes
        ),
        GRB.MAXIMIZE
    )

    model.optimize()

    if model.status != GRB.OPTIMAL:
        return {"error": "Gurobi did not find an optimal solution."}

    assignments = []
    for g in groups:
        for h in hikes:
            if x[g, h].X > 0.5:
                assignments.append({
                    "group_index": int(g),
                    "driver_name": str(request_df.loc[g, "Driver name"]),
                    "assigned_hike": str(hike_df.loc[h, "gorilla_family"]),
                    "hike_difficulty": int(hike_df.loc[h, "difficulty"]),
                    "group_difficulty": int(request_df.loc[g, "Desired Difficulty Level"]),
                    "reason": str(request_df.loc[g, "Reason for Request"])
                })

    return {"assignments": assignments}
