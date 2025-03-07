import tkinter as tk
from tkinter import ttk
from math import exp, factorial

class CombinedFootballBettingModel:
    def __init__(self, root):
        self.root = root
        self.root.title("Combined Football Betting Model")
        self.create_widgets()
        # History maintained for potential future use
        self.history = {
            "home_xg": [],
            "away_xg": [],
            "home_sot": [],
            "away_sot": [],
            "home_possession": [],
            "away_possession": []
        }
        self.history_length = 10  # last 10 updates

    def create_widgets(self):
        # Create a scrollable frame
        self.canvas = tk.Canvas(self.root)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Combined fields from both models
        self.fields = {
            "Home Avg Goals Scored": tk.DoubleVar(),
            "Home Avg Goals Conceded": tk.DoubleVar(),
            "Away Avg Goals Scored": tk.DoubleVar(),
            "Away Avg Goals Conceded": tk.DoubleVar(),
            "Home Xg": tk.DoubleVar(),
            "Away Xg": tk.DoubleVar(),
            "Elapsed Minutes": tk.DoubleVar(),
            "Home Goals": tk.IntVar(),
            "Away Goals": tk.IntVar(),
            "In-Game Home Xg": tk.DoubleVar(),
            "In-Game Away Xg": tk.DoubleVar(),
            "Home Possession %": tk.DoubleVar(),
            "Away Possession %": tk.DoubleVar(),
            "Home Shots on Target": tk.IntVar(),
            "Away Shots on Target": tk.IntVar(),
            "Home Opp Box Touches": tk.DoubleVar(),
            "Away Opp Box Touches": tk.DoubleVar(),
            "Home Corners": tk.DoubleVar(),
            "Away Corners": tk.DoubleVar(),
            "Live Next Goal Odds": tk.DoubleVar(),
            "Live Odds Home": tk.DoubleVar(),
            "Live Odds Draw": tk.DoubleVar(),
            "Live Odds Away": tk.DoubleVar(),
            "Account Balance": tk.DoubleVar()
        }
        row = 0
        for field, var in self.fields.items():
            label = ttk.Label(self.scrollable_frame, text=field)
            label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
            entry = ttk.Entry(self.scrollable_frame, textvariable=var)
            entry.grid(row=row, column=1, padx=5, pady=5)
            row += 1

        # Calculate and Reset buttons
        calc_button = ttk.Button(self.scrollable_frame, text="Calculate", command=self.calculate_all)
        calc_button.grid(row=row, column=0, columnspan=2, pady=10)
        row += 1

        reset_button = ttk.Button(self.scrollable_frame, text="Reset Fields", command=self.reset_fields)
        reset_button.grid(row=row, column=0, columnspan=2, pady=10)
        row += 1

        # Output area for both Next Goal and Match Odds calculations
        self.output_text = tk.Text(self.scrollable_frame, height=20, wrap="word")
        self.output_text.grid(row=row, column=0, columnspan=2, pady=10)
        # Configure color tags
        self.output_text.tag_configure("lay", foreground="red")
        self.output_text.tag_configure("back", foreground="blue")
        self.output_text.tag_configure("normal", foreground="black")
        self.output_text.config(state="disabled")

    def reset_fields(self):
        for var in self.fields.values():
            if isinstance(var, tk.DoubleVar):
                var.set(0.0)
            elif isinstance(var, tk.IntVar):
                var.set(0)
        self.history = {
            "home_xg": [],
            "away_xg": [],
            "home_sot": [],
            "away_sot": [],
            "home_possession": [],
            "away_possession": []
        }

    # ----- Common Methods -----
    def zero_inflated_poisson_probability(self, lam, k, p_zero=0.06):
        if k == 0:
            return p_zero + (1 - p_zero) * exp(-lam)
        return (1 - p_zero) * ((lam ** k) * exp(-lam)) / factorial(k)

    def time_decay_adjustment(self, lambda_xg, elapsed_minutes, in_game_xg):
        remaining_minutes = 90 - elapsed_minutes
        base_decay = exp(-0.01 * elapsed_minutes)
        base_decay = max(base_decay, 0.6)
        if in_game_xg > 1.5:
            base_decay *= 1.15
        elif remaining_minutes < 10:
            base_decay *= 0.65
        adjusted_lambda = lambda_xg * base_decay
        return max(0.1, adjusted_lambda)

    def adjust_xg_for_scoreline(self, home_goals, away_goals, lambda_home, lambda_away, elapsed_minutes):
        goal_diff = home_goals - away_goals
        if goal_diff == 1:
            lambda_home *= 0.9
            lambda_away *= 1.2
        elif goal_diff == -1:
            lambda_home *= 1.2
            lambda_away *= 0.9
        elif goal_diff == 0:
            lambda_home *= 1.05
            lambda_away *= 1.05
        elif abs(goal_diff) >= 2:
            lambda_home *= 0.8
            lambda_away *= 1.3 if goal_diff > 0 else 0.8
        if elapsed_minutes > 75 and abs(goal_diff) >= 1:
            lambda_home *= 0.85
            lambda_away *= 1.15 if goal_diff > 0 else 0.85
        return lambda_home, lambda_away

    def update_history(self, key, value):
        if key not in self.history:
            self.history[key] = []
        if len(self.history[key]) >= self.history_length:
            self.history[key].pop(0)
        self.history[key].append(value)

    def dynamic_kelly(self, edge):
        # Use quarter Kelly (25% of the edge)
        kelly_fraction = 0.25 * edge
        return max(0, kelly_fraction)

    # ----- Combined Calculation -----
    def calculate_all(self):
        f = self.fields
        # Retrieve common inputs
        home_xg = f["Home Xg"].get()
        away_xg = f["Away Xg"].get()
        elapsed_minutes = f["Elapsed Minutes"].get()
        home_goals = f["Home Goals"].get()
        away_goals = f["Away Goals"].get()
        in_game_home_xg = f["In-Game Home Xg"].get()
        in_game_away_xg = f["In-Game Away Xg"].get()
        home_possession = f["Home Possession %"].get()
        away_possession = f["Away Possession %"].get()
        home_avg_goals_scored = f["Home Avg Goals Scored"].get()
        home_avg_goals_conceded = f["Home Avg Goals Conceded"].get()
        away_avg_goals_scored = f["Away Avg Goals Scored"].get()
        away_avg_goals_conceded = f["Away Avg Goals Conceded"].get()
        home_sot = f["Home Shots on Target"].get()
        away_sot = f["Away Shots on Target"].get()
        home_op_box_touches = f["Home Opp Box Touches"].get()
        away_op_box_touches = f["Away Opp Box Touches"].get()
        home_corners = f["Home Corners"].get()
        away_corners = f["Away Corners"].get()
        live_next_goal_odds = f["Live Next Goal Odds"].get()
        live_odds_home = f["Live Odds Home"].get()
        live_odds_draw = f["Live Odds Draw"].get()
        live_odds_away = f["Live Odds Away"].get()
        account_balance = f["Account Balance"].get()

        # Update history
        self.update_history("home_xg", home_xg)
        self.update_history("away_xg", away_xg)
        self.update_history("home_sot", home_sot)
        self.update_history("away_sot", away_sot)
        self.update_history("home_possession", home_possession)
        self.update_history("away_possession", away_possession)

        remaining_minutes = 90 - elapsed_minutes

        # --- Next Goal Calculation ---
        lambda_home = self.time_decay_adjustment(in_game_home_xg + (home_xg * remaining_minutes / 90),
                                                elapsed_minutes, in_game_home_xg)
        lambda_away = self.time_decay_adjustment(in_game_away_xg + (away_xg * remaining_minutes / 90),
                                                elapsed_minutes, in_game_away_xg)
        lambda_home, lambda_away = self.adjust_xg_for_scoreline(home_goals, away_goals,
                                                                lambda_home, lambda_away, elapsed_minutes)
        lambda_home = (lambda_home * 0.85) + ((home_avg_goals_scored / max(0.75, away_avg_goals_conceded)) * 0.15)
        lambda_away = (lambda_away * 0.85) + ((away_avg_goals_scored / max(0.75, home_avg_goals_conceded)) * 0.15)
        lambda_home *= 1 + ((home_possession - 50) / 200)
        lambda_away *= 1 + ((away_possession - 50) / 200)
        if in_game_home_xg > 1.2:
            lambda_home *= 1.15
        if in_game_away_xg > 1.2:
            lambda_away *= 1.15
        lambda_home *= 1 + (home_sot / 20)
        lambda_away *= 1 + (away_sot / 20)
        lambda_home *= 1 + ((home_op_box_touches - 20) / 200)
        lambda_away *= 1 + ((away_op_box_touches - 20) / 200)
        lambda_home *= 1 + ((home_corners - 4) / 50)
        lambda_away *= 1 + ((away_corners - 4) / 50)

        goal_probability = 1 - exp(-((lambda_home + lambda_away) * remaining_minutes / 45))
        goal_probability = max(0.30, min(0.90, goal_probability))
        fair_next_goal_odds = 1 / goal_probability

        # Build the Next Goal output
        lines_ng = []
        lines_ng.append("--- Next Goal Calculation ---")
        lines_ng.append(f"Goal Probability: {goal_probability:.2%} → Fair Next Goal Odds: {fair_next_goal_odds:.2f}")

        recommendation_ng = "none"
        if live_next_goal_odds > 0:
            if fair_next_goal_odds > live_next_goal_odds:
                edge_ng = (fair_next_goal_odds - live_next_goal_odds) / fair_next_goal_odds
                if edge_ng > 0:
                    kelly_fraction = self.dynamic_kelly(edge_ng)
                    liability = account_balance * kelly_fraction
                    profit = liability / (live_next_goal_odds - 1) if (live_next_goal_odds - 1) > 0 else 0
                    lines_ng.append(f"Lay Next Goal at {live_next_goal_odds:.2f} | "
                                    f"Liability: {liability:.2f} | Profit: {profit:.2f}")
                    recommendation_ng = "lay"
                else:
                    lines_ng.append("No value bet found for Next Goal")
            elif live_next_goal_odds > fair_next_goal_odds:
                edge_ng = (live_next_goal_odds - fair_next_goal_odds) / fair_next_goal_odds
                if edge_ng > 0:
                    kelly_fraction = self.dynamic_kelly(edge_ng)
                    stake = account_balance * kelly_fraction
                    profit = stake * (live_next_goal_odds - 1)
                    lines_ng.append(f"Back Next Goal at {live_next_goal_odds:.2f} | "
                                    f"Stake: {stake:.2f} | Profit: {profit:.2f}")
                    recommendation_ng = "back"
                else:
                    lines_ng.append("No value bet found for Next Goal")
            else:
                lines_ng.append("No bet found for Next Goal")
        else:
            lines_ng.append("No bet found for Next Goal")

        # --- Match Odds Calculation ---
        lambda_home_mo = self.time_decay_adjustment(in_game_home_xg + (home_xg * remaining_minutes / 90),
                                                    elapsed_minutes, in_game_home_xg)
        lambda_away_mo = self.time_decay_adjustment(in_game_away_xg + (away_xg * remaining_minutes / 90),
                                                    elapsed_minutes, in_game_away_xg)
        lambda_home_mo, lambda_away_mo = self.adjust_xg_for_scoreline(home_goals, away_goals,
                                                                      lambda_home_mo, lambda_away_mo, elapsed_minutes)
        lambda_home_mo = (lambda_home_mo * 0.85) + ((home_avg_goals_scored / max(0.75, away_avg_goals_conceded)) * 0.15)
        lambda_away_mo = (lambda_away_mo * 0.85) + ((away_avg_goals_scored / max(0.75, home_avg_goals_conceded)) * 0.15)
        lambda_home_mo *= 1 + ((home_possession - 50) / 200)
        lambda_away_mo *= 1 + ((away_possession - 50) / 200)
        if in_game_home_xg > 1.2:
            lambda_home_mo *= 1.15
        if in_game_away_xg > 1.2:
            lambda_away_mo *= 1.15
        lambda_home_mo *= 1 + (home_sot / 20)
        lambda_away_mo *= 1 + (away_sot / 20)
        lambda_home_mo *= 1 + ((home_op_box_touches - 20) / 200)
        lambda_away_mo *= 1 + ((away_op_box_touches - 20) / 200)
        lambda_home_mo *= 1 + ((home_corners - 4) / 50)
        lambda_away_mo *= 1 + ((away_corners - 4) / 50)

        # Compute outcome probabilities
        home_win_prob = 0
        away_win_prob = 0
        draw_prob = 0
        for gh in range(6):
            for ga in range(6):
                prob = (self.zero_inflated_poisson_probability(lambda_home_mo, gh) *
                        self.zero_inflated_poisson_probability(lambda_away_mo, ga))
                if home_goals + gh > away_goals + ga:
                    home_win_prob += prob
                elif home_goals + gh < away_goals + ga:
                    away_win_prob += prob
                else:
                    draw_prob += prob
        total = home_win_prob + away_win_prob + draw_prob
        if total > 0:
            home_win_prob /= total
            away_win_prob /= total
            draw_prob /= total

        fair_odds_home = 1 / home_win_prob if home_win_prob > 0 else float('inf')
        fair_odds_draw = 1 / draw_prob if draw_prob > 0 else float('inf')
        fair_odds_away = 1 / away_win_prob if away_win_prob > 0 else float('inf')

        lines_mo = []
        lines_mo.append("--- Match Odds Calculation ---")
        lines_mo.append(f"Fair Odds - Home: {fair_odds_home:.2f}, Draw: {fair_odds_draw:.2f}, Away: {fair_odds_away:.2f}")
        lines_mo.append(f"Live Odds - Home: {live_odds_home:.2f}, Draw: {live_odds_draw:.2f}, Away: {live_odds_away:.2f}")

        # Home market
        if fair_odds_home > live_odds_home:
            edge = (fair_odds_home - live_odds_home) / fair_odds_home
            liability = account_balance * self.dynamic_kelly(edge)
            lay_stake = liability / (live_odds_home - 1) if (live_odds_home - 1) > 0 else 0
            lines_mo.append(f"Lay Home: Edge: {edge:.2%}, Liability: {liability:.2f}, Lay Stake: {lay_stake:.2f}")
        elif fair_odds_home < live_odds_home:
            edge = (live_odds_home - fair_odds_home) / fair_odds_home
            stake = account_balance * self.dynamic_kelly(edge)
            profit = stake * (live_odds_home - 1)
            lines_mo.append(f"Back Home: Edge: {edge:.2%}, Stake: {stake:.2f}, Profit: {profit:.2f}")
        else:
            lines_mo.append("Home: No clear edge.")

        # Draw market
        if fair_odds_draw > live_odds_draw:
            edge = (fair_odds_draw - live_odds_draw) / fair_odds_draw
            liability = account_balance * self.dynamic_kelly(edge)
            lay_stake = liability / (live_odds_draw - 1) if (live_odds_draw - 1) > 0 else 0
            lines_mo.append(f"Lay Draw: Edge: {edge:.2%}, Liability: {liability:.2f}, Lay Stake: {lay_stake:.2f}")
        elif fair_odds_draw < live_odds_draw:
            edge = (live_odds_draw - fair_odds_draw) / fair_odds_draw
            stake = account_balance * self.dynamic_kelly(edge)
            profit = stake * (live_odds_draw - 1)
            lines_mo.append(f"Back Draw: Edge: {edge:.2%}, Stake: {stake:.2f}, Profit: {profit:.2f}")
        else:
            lines_mo.append("Draw: No clear edge.")

        # Away market
        if fair_odds_away > live_odds_away:
            edge = (fair_odds_away - live_odds_away) / fair_odds_away
            liability = account_balance * self.dynamic_kelly(edge)
            lay_stake = liability / (live_odds_away - 1) if (live_odds_away - 1) > 0 else 0
            lines_mo.append(f"Lay Away: Edge: {edge:.2%}, Liability: {liability:.2f}, Lay Stake: {lay_stake:.2f}")
        elif fair_odds_away < live_odds_away:
            edge = (live_odds_away - fair_odds_away) / fair_odds_away
            stake = account_balance * self.dynamic_kelly(edge)
            profit = stake * (live_odds_away - 1)
            lines_mo.append(f"Back Away: Edge: {edge:.2%}, Stake: {stake:.2f}, Profit: {profit:.2f}")
        else:
            lines_mo.append("Away: No clear edge.")

        # Combine all lines, add some blank lines for spacing
        combined_lines = []
        combined_lines.extend(lines_ng)
        combined_lines.append("")  # Blank line
        combined_lines.extend(lines_mo)
        combined_lines.append("")  # Another blank line at the end

        # Now insert line by line with color tags
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", tk.END)

        for line in combined_lines:
            # Decide which tag to use based on presence of "Lay" or "Back"
            # (This is a simple approach; adjust logic if needed.)
            if "Lay " in line:
                self.output_text.insert(tk.END, line + "\n", "lay")
            elif "Back " in line:
                self.output_text.insert(tk.END, line + "\n", "back")
            else:
                self.output_text.insert(tk.END, line + "\n", "normal")

        self.output_text.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = CombinedFootballBettingModel(root)
    root.mainloop()
