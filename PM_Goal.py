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
        
        # Live odds for Over 2.5
        live_over_odds  = float(entries["entry_live_over_odds"].get())
        
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
        # (We only need the live over odds here)
        live_over_prob  = 1 / live_over_odds  if live_over_odds  > 0 else 0
        
        # For normalization, assume over and under probabilities add up to 1
        # In this model, live_over_prob is considered alongside its complement
        live_under_prob = 1 - live_over_prob
        
        # --- 5) Blend the model's probabilities with the live probabilities ---
        blend_factor = 0.3  # 30% from market, 70% from model
        final_over_prob  = over_prob_model  * (1 - blend_factor) + live_over_prob  * blend_factor
        final_under_prob = under_prob_model * (1 - blend_factor) + live_under_prob * blend_factor
        
        # Normalize final probabilities
        sum_final = final_over_prob + final_under_prob
        if sum_final > 0:
            final_over_prob  /= sum_final
            final_under_prob /= sum_final
        
        # --- 6) Convert final probabilities to final “Fair Odds” (blended) ---
        final_fair_over_odds  = 1 / final_over_prob  if final_over_prob  > 0 else float('inf')
        
        # --- 7) Compare fair odds vs live odds for Over 2.5 and determine text color ---
        # If fair odds are higher than live odds, color is red; if lower, blue.
        if final_fair_over_odds > live_over_odds:
            over_color = "red"
        else:
            over_color = "blue"
        
        # --- 8) Display the Over result in the bottom text window ---
        output_text.config(state="normal")
        output_text.delete("1.0", tk.END)
        
        over_line  = f"Over 2.5 Goals: Fair {final_fair_over_odds:.2f} vs Live {live_over_odds:.2f}\n"
        output_text.insert(tk.END, over_line, over_color)
        output_text.config(state="disabled")
        
    except ValueError:
        output_text.config(state="normal")
        output_text.delete("1.0", tk.END)
        output_text.insert(tk.END, "Please enter valid numerical values.", "error")
        output_text.config(state="disabled")

def reset_fields():
    for entry in entries.values():
        entry.delete(0, tk.END)
    output_text.config(state="normal")
    output_text.delete("1.0", tk.END)
    output_text.config(state="disabled")

# --- GUI Layout ---
root = tk.Tk()
root.title("Odds Apex Pre-Match")

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
    "entry_live_over_odds":   tk.Entry(root)
}

labels_text = [
    "Avg Goals Home Scored", "Avg Goals Home Conceded", "Avg Goals Away Scored", "Avg Goals Away Conceded",
    "Injuries Home", "Injuries Away", "Position Home", "Position Away",
    "Form Home", "Form Away", "Home xG Scored", "Away xG Scored",
    "Home xG Conceded", "Away xG Conceded", "Live Over 2.5 Odds"
]

for i, (key, label_text) in enumerate(zip(entries.keys(), labels_text)):
    label = tk.Label(root, text=label_text)
    label.grid(row=i, column=0, padx=5, pady=5, sticky="e")
    entries[key].grid(row=i, column=1, padx=5, pady=5)

calculate_button = tk.Button(root, text="Calculate Odds", command=calculate_probabilities)
calculate_button.grid(row=len(entries), column=0, columnspan=2, padx=5, pady=10)

reset_button = tk.Button(root, text="Reset All Fields", command=reset_fields)
reset_button.grid(row=len(entries)+1, column=0, columnspan=2, padx=5, pady=10)

# --- Create a bottom text window for output ---
output_text = tk.Text(root, height=5, width=50)
output_text.grid(row=len(entries)+2, column=0, columnspan=2, padx=5, pady=10)
output_text.config(state="disabled")

# --- Configure tags for color formatting ---
output_text.tag_config("red", foreground="red")
output_text.tag_config("blue", foreground="blue")
output_text.tag_config("error", foreground="red")

root.mainloop()
