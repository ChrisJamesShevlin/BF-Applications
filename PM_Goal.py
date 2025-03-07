import tkinter as tk
import math

def zip_probability(lam, k, p_zero=0.0):
    """
    Zero-inflated Poisson probability.
    p_zero is set to 0.0 here to remove extra weighting for 0 goals.
    """
    if k == 0:
        return p_zero + (1 - p_zero) * math.exp(-lam)
    return (1 - p_zero) * ((lam ** k) * math.exp(-lam)) / math.factorial(k)

def dynamic_kelly(edge):
    """
    Returns the Kelly fraction for back bets based on the edge.
    The Kelly fraction is 0.05 times the edge.
    """
    kelly_fraction = 0.05 * edge
    return max(0, kelly_fraction)

def dynamic_kelly_lay(edge):
    """
    Returns the Kelly fraction for lay bets based on the edge.
    This uses a quarter Kelly (25% Kelly), i.e. 0.25 times the edge.
    """
    kelly_fraction = 0.25 * edge
    return max(0, kelly_fraction)

def calculate_probabilities():
    try:
        # --- 1) Retrieve all inputs ---
        avg_goals_home_scored   = float(entries["entry_home_scored"].get())
        avg_goals_home_conceded = float(entries["entry_home_conceded"].get())
        avg_goals_away_scored   = float(entries["entry_away_scored"].get())
        avg_goals_away_conceded = float(entries["entry_away_conceded"].get())
        
        injuries_home           = int(entries["entry_injuries_home"].get())
        injuries_away           = int(entries["entry_injuries_away"].get())
        position_home           = int(entries["entry_position_home"].get())
        position_away           = int(entries["entry_position_away"].get())
        form_home               = int(entries["entry_form_home"].get())
        form_away               = int(entries["entry_form_away"].get())
        
        home_xg_scored   = float(entries["entry_home_xg_scored"].get())
        away_xg_scored   = float(entries["entry_away_xg_scored"].get())
        home_xg_conceded = float(entries["entry_home_xg_conceded"].get())
        away_xg_conceded = float(entries["entry_away_xg_conceded"].get())
        
        # Live odds for Under/Over 2.5
        live_under_odds = float(entries["entry_live_under_odds"].get())
        live_over_odds  = float(entries["entry_live_over_odds"].get())
        
        # Account Balance for staking recommendations
        account_balance = float(entries["entry_account_balance"].get())
        
        # --- 2) Calculate raw expected goals for each team ---
        adjusted_home_goals = ((avg_goals_home_scored + home_xg_scored +
                                avg_goals_away_conceded + away_xg_conceded) / 4)
        adjusted_home_goals *= (1 - 0.03 * injuries_home)
        adjusted_home_goals += form_home * 0.1 - position_home * 0.01
        
        adjusted_away_goals = ((avg_goals_away_scored + away_xg_scored +
                                avg_goals_home_conceded + home_xg_conceded) / 4)
        adjusted_away_goals *= (1 - 0.03 * injuries_away)
        adjusted_away_goals += form_away * 0.1 - position_away * 0.01
        
        # --- 3) Model probabilities for Under & Over 2.5 using Poisson ---
        goal_range = 10
        under_prob_model = 0.0
        for i in range(goal_range):
            for j in range(goal_range):
                if (i + j) <= 2:
                    prob_i = zip_probability(adjusted_home_goals, i)
                    prob_j = zip_probability(adjusted_away_goals, j)
                    under_prob_model += prob_i * prob_j
        over_prob_model = 1 - under_prob_model
        
        # --- 4) Convert live odds to implied probabilities and normalize them ---
        live_under_prob = 1 / live_under_odds if live_under_odds > 0 else 0
        live_over_prob  = 1 / live_over_odds  if live_over_odds  > 0 else 0
        
        sum_live_probs = live_under_prob + live_over_prob
        if sum_live_probs > 0:
            live_under_prob /= sum_live_probs
            live_over_prob  /= sum_live_probs
        
        # --- 5) Blend the model's probabilities with the live probabilities ---
        blend_factor = 0.3  # 30% from market, 70% from model
        final_under_prob = under_prob_model * (1 - blend_factor) + live_under_prob * blend_factor
        final_over_prob  = over_prob_model  * (1 - blend_factor) + live_over_prob  * blend_factor
        
        sum_final = final_under_prob + final_over_prob
        if sum_final > 0:
            final_under_prob /= sum_final
            final_over_prob  /= sum_final
        
        # --- 6) Convert final probabilities to final “Fair Odds” (blended) ---
        final_fair_under_odds = 1 / final_under_prob if final_under_prob > 0 else float('inf')
        final_fair_over_odds  = 1 / final_over_prob  if final_over_prob  > 0 else float('inf')
        
        # --- 7) Apply Kelly staking plan for Under 2.5 (calculated but hidden) ---
        if final_fair_under_odds > live_under_odds:
            edge_lay = (final_fair_under_odds - live_under_odds) / final_fair_under_odds
            # Use quarter Kelly for lay bets
            kelly_fraction_lay = dynamic_kelly_lay(edge_lay)
            liability_lay = account_balance * kelly_fraction_lay
            stake_under = liability_lay / (live_under_odds - 1) if (live_under_odds - 1) > 0 else 0
            under_recommendation = f"Lay Under at {live_under_odds:.2f} | Stake: {stake_under:.2f} | Liability: {liability_lay:.2f}"
        elif final_fair_under_odds < live_under_odds:
            edge_back = (live_under_odds - final_fair_under_odds) / final_fair_under_odds
            kelly_fraction_back = dynamic_kelly(edge_back)
            stake_under = account_balance * kelly_fraction_back
            potential_profit = stake_under * (live_under_odds - 1)
            under_recommendation = f"Back Under at {live_under_odds:.2f} | Stake: {stake_under:.2f} | Potential Profit: {potential_profit:.2f}"
        else:
            under_recommendation = "No value on Under bet"
        
        # --- 8) Apply Kelly staking plan for Over 2.5 (display only lay bets) ---
        if final_fair_over_odds > live_over_odds:
            edge_lay = (final_fair_over_odds - live_over_odds) / final_fair_over_odds
            # Use quarter Kelly for lay bets
            kelly_fraction_lay = dynamic_kelly_lay(edge_lay)
            liability_lay = account_balance * kelly_fraction_lay
            stake_over = liability_lay / (live_over_odds - 1) if (live_over_odds - 1) > 0 else 0
            over_recommendation = f"Lay Over at {live_over_odds:.2f} | Stake: {stake_over:.2f} | Liability: {liability_lay:.2f}"
            text_color = "green"
        else:
            over_recommendation = "No bet found"
            text_color = "red"
        
        # --- 9) Display the Over bet result only ---
        result_text = (
            f"Over 2.5 Goals: Fair {final_fair_over_odds:.2f} vs Live {live_over_odds:.2f}\n"
            f"Recommendation: {over_recommendation}"
        )
        result_label.config(text=result_text, foreground=text_color)
        
    except ValueError:
        result_label.config(text="Please enter valid numerical values.", foreground="red")

def reset_fields():
    for entry in entries.values():
        entry.delete(0, tk.END)
    result_label.config(text="")

# --- GUI Layout ---
root = tk.Tk()
root.title("Odds Apex PM Lay Over")

entries = {
    "entry_home_scored":      tk.Entry(root),
    "entry_home_conceded":    tk.Entry(root),
    "entry_away_scored":      tk.Entry(root),
    "entry_away_conceded":    tk.Entry(root),
    "entry_injuries_home":    tk.Entry(root),
    "entry_injuries_away":    tk.Entry(root),
    "entry_position_home":    tk.Entry(root),
    "entry_position_away":    tk.Entry(root),
    "entry_form_home":        tk.Entry(root),
    "entry_form_away":        tk.Entry(root),
    "entry_home_xg_scored":   tk.Entry(root),
    "entry_away_xg_scored":   tk.Entry(root),
    "entry_home_xg_conceded": tk.Entry(root),
    "entry_away_xg_conceded": tk.Entry(root),
    "entry_live_under_odds":  tk.Entry(root),
    "entry_live_over_odds":   tk.Entry(root),
    "entry_account_balance":  tk.Entry(root)
}

labels_text = [
    "Avg Goals Home Scored", "Avg Goals Home Conceded", "Avg Goals Away Scored", "Avg Goals Away Conceded",
    "Injuries Home", "Injuries Away", "Position Home", "Position Away",
    "Form Home", "Form Away", "Home xG Scored", "Away xG Scored",
    "Home xG Conceded", "Away xG Conceded", "Live Under 2.5 Odds", "Live Over 2.5 Odds",
    "Account Balance"
]

for i, (key, label_text) in enumerate(zip(entries.keys(), labels_text)):
    label = tk.Label(root, text=label_text)
    label.grid(row=i, column=0, padx=5, pady=5, sticky="e")
    entries[key].grid(row=i, column=1, padx=5, pady=5)

result_label = tk.Label(root, text="", justify="left")
result_label.grid(row=len(entries), column=0, columnspan=2, padx=5, pady=5)

calculate_button = tk.Button(root, text="Calculate Over/Under Odds & Stakes", command=calculate_probabilities)
calculate_button.grid(row=len(entries)+1, column=0, columnspan=2, padx=5, pady=10)

reset_button = tk.Button(root, text="Reset All Fields", command=reset_fields)
reset_button.grid(row=len(entries)+2, column=0, columnspan=2, padx=5, pady=10)

root.mainloop()
