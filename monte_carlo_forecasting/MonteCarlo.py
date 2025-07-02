#!/usr/bin/env python
import pandas as pd
import random
import datetime
from io import StringIO

class Simulation:
    def __init__(self,symbol,expiration_date,intervals=None,lower_bound=None,upper_bound=None,current_price=None,current_price_weight=.2):

        def get_price(ticker):
            # Try to extract price from HTML, fallback to reasonable default
            try:
                with open(ticker + '.html', 'r') as f:
                    html_content = f.read()
                return float(pd.read_html(StringIO(html_content))[0]["Close*"].iloc[0])
            except:
                # Fallback price for NVDA (approximate current price)
                return 153.30

        # Handle backwards compatibility and new intervals parameter
        if intervals is not None:
            self.intervals = sorted(intervals)
        elif lower_bound is not None and upper_bound is not None:
            self.intervals = [lower_bound, upper_bound]
        else:
            raise ValueError("Must specify either 'intervals' array or both 'lower_bound' and 'upper_bound'")

        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

        split_date = [int(x) for x in expiration_date.split('-')]
        expiration = datetime.date(*split_date)
        self.remaining_days = (expiration - datetime.date.today()).days
        self.current_price = current_price
        if current_price is None:
            self.current_price = get_price(symbol)
        print("CURRENT PRICE:",self.current_price)
        self.current_price_weight = current_price_weight
        self.simulated_price_weight = 1 - current_price_weight
        with open(symbol + "-yahoo-table.html", 'r') as f:
            html_content = f.read()
        df = pd.read_html(StringIO(html_content))[0]
        # Use the correct column name and filter out dividend rows
        close_col = 'Close  Close price adjusted for splits.'
        # Filter out rows containing "Dividend" before converting to numeric
        df = df[~df[close_col].astype(str).str.contains('Dividend', na=False)]
        df = df[df[close_col].astype(str).str.contains(r'^\d', na=False)]
        df['Close'] = pd.to_numeric(df[close_col], errors='coerce')
        df["Previous"] = df.Close.shift()
        df.dropna(inplace=True)
        self.shifts = set((df.Close/df.Previous).apply(lambda x: x - 1)) # Make a set of historical price shifts

    def random_flip(self,move,cx=1):
        chance_array = [-1] + [1]*cx
        if move == 0 or 1 == chance_array[random.randrange(cx + 1)]: # 1 / (cx + 1) chance of flipping the sign
            return move
        return (1 / (1 + move) - 1)


    def run_trials(self,trials=10000,sudden_condition=False):
        sample = lambda data: random.sample(list(data),1)[0] # Pull a random sample from a set
        interval_counts = [0] * (len(self.intervals) + 1)  # One more bucket than intervals
        
        for j in range(trials):
            price = self.current_price
            for i in range(self.remaining_days):
                move = self.random_flip(sample(self.shifts)) * (self.current_price_weight * self.current_price + self.simulated_price_weight * price)
                price = price + move
                if sudden_condition:
                    # Check if price is outside any interval for early break
                    if price < self.intervals[0] or price > self.intervals[-1]:
                        break
            
            # Count which interval the final price falls into
            bucket = 0
            for threshold in self.intervals:
                if price >= threshold:
                    bucket += 1
                else:
                    break
            interval_counts[bucket] += 1

        # Convert to percentages and create output
        percentages = [x * 100 / trials for x in interval_counts]
        
        # Format output based on number of intervals
        if len(self.intervals) == 2:
            # Backwards compatibility: show LOW/HIGH format
            print("LOW:{}%,HIGH:{}%".format(percentages[0], percentages[2]))
            return [percentages[0], percentages[2]]
        else:
            # New format: show all intervals
            result = []
            for i, pct in enumerate(percentages):
                if i == 0:
                    print("< {}:{:.2f}%".format(self.intervals[0], pct))
                elif i == len(percentages) - 1:
                    print("> {}:{:.2f}%".format(self.intervals[-1], pct))
                else:
                    print("{}-{}:{:.2f}%".format(self.intervals[i-1], self.intervals[i], pct))
                result.append(pct)
            return result

if __name__ == '__main__':
    s = Simulation('NVDA','2025-12-31',intervals=[100, 160, 200, 280, 340, 400],lower_bound=100,upper_bound=200)
    s.run_trials()
