import pandas as pd
from gurobipy import Model, GRB, quicksum

# --- Sample Input Data ---

hikes = [
    {
        "gorilla_family": "Kwitonza",
        "difficulty": 2,
        "description_binary": {"rocky": 1, "wet": 0, "steep": 1}
    },
    {
        "gorilla_family": "Igisha",
        "difficulty": 3,
        "description_binary": {"rocky": 0, "wet": 1, "steep": 1}
    }
]

requests = [
    {
        "Driver name": "Elvis",
        "Total tourists": 2,
        "For each group, list the type of hike. either easy, medium or, hard and any reasons why. Example: Group 1 wants easy because one of the members is old.": "Easy because one guest is old",
        "Any other requests": "N/A"
    },
    {
        "Driver name": "Fabrice",
        "Total tourists": 3,
        "For each group, list the type of hike. either easy, medium or, hard and any reasons why. Example: Group 1 wants easy because one of the members is old.": "Medium",
        "Any other requests": "Fit hikers"
    }
]

# --- Utilities ---

def infer_difficulty(text):
    text = str(text).lower()
    if "easy" in text: return 1
    if "medium" in text: return 2
    if "hard" in text: return 3
    return 2

def extract_reason(row):
    combined = " ".join(str(v).lower() for v in row.values)  # FIXED
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
        return int(float(value))
    except:
        return 1

# --- Preprocess DataFrames ---

hike_df = pd.DataFrame(hikes)
difficulty_vals = []
for val in hike_df["difficulty"]:
    try:
        rounded = round(float(val))
        difficulty_vals.append(int(rounded))
    except:
        difficulty_vals.append(2)
hike_df["difficulty"] = difficulty_vals
hike_df["rocky"] = hike_df["description_binary"].apply(lambda x: x.get("rocky", 0))
hike_df["wet"] = hike_df["description_binary"].apply(lambda x: x.get("wet", 0))
hike_df["steep"] = hike_df["description_binary"].apply(lambda x: x.get("steep", 0))

request_df = pd.DataFrame(requests).fillna("")
reason_col = "For each group, list the type of hike. either easy, medium or, hard and any reasons why. Example: Group 1 wants easy because one of the members is old."
request_df["Desired Difficulty Level"] = request_df[reason_col].apply(infer_difficulty)
request_df["Reason for Request"] = request_df.apply(extract_reason, axis=1)
request_df["Total tourists"] = request_df["Total tourists"].apply(get_tourist_count)

# --- Gurobi Model ---

model = Model("local_assignment")
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
    print("❌ Gurobi did not find an optimal solution.")
else:
    print("\n✅ Assignments:")
    for g in groups:
        for h in hikes:
            if x[g, h].X > 0.5:
                print(f"Group {g}:")
                print(f"  Driver: {request_df.loc[g, 'Driver name']}")
                print(f"  Assigned to: {hike_df.loc[h, 'gorilla_family']}")
                print(f"  Hike Difficulty: {hike_df.loc[h, 'difficulty']}")
                print(f"  Group Requested: {request_df.loc[g, 'Desired Difficulty Level']} — Reason: {request_df.loc[g, 'Reason for Request']}")
                print()
