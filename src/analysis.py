"""Fake discount detection based on the price history we collected."""

MIN_DAYS = 7          # we need at least a week of data before judging
SAME_PRICE = 0.02     # prices within 2% of each other count as "the same"
REAL_DROP = 0.05      # a real deal is at least 5% below the usual price
SPIKE = 0.10          # a price at least 10% above usual counts as a spike


def check_discount(daily):
    """
    Decide whether a product's discount looks real.

    `daily` is a list of (price, original_price) pairs, one per day, oldest first.
    Returns a dictionary with a verdict and the reasons behind it.
    """
    if not daily:
        return {"verdict": "No data", "reasons": ["No prices have been collected yet."]}

    prices = [price for price, _ in daily]
    current, claimed_original = daily[-1]
    days = len(daily)

    if not claimed_original or claimed_original <= current:
        return {"verdict": "No discount claimed",
                "reasons": ["The store is not showing a sale price right now."]}

    claimed_off = round((1 - current / claimed_original) * 100)

    if days < MIN_DAYS:
        return {"verdict": "Not enough data",
                "reasons": [f"The store claims {claimed_off}% off, but we have only "
                            f"{days} day(s) of history. We need at least {MIN_DAYS}."]}

    earlier = sorted(prices[:-1])
    usual = earlier[len(earlier) // 2]          # median of earlier prices
    highest_seen = max(prices)
    reasons = []

    # Rule 1: was the product ever sold at the "original" price?
    never_at_original = highest_seen < claimed_original * (1 - SAME_PRICE)
    if never_at_original:
        reasons.append(f"In {days} days it was never sold at the 'original' price of "
                       f"{claimed_original:,.0f}. The highest price we saw was "
                       f"{highest_seen:,.0f}.")

    # Rule 2: is today's price actually lower than usual?
    no_real_drop = current >= usual * (1 - REAL_DROP)
    if no_real_drop:
        reasons.append(f"Today's price ({current:,.0f}) is about the same as its usual "
                       f"price ({usual:,.0f}), so nothing actually got cheaper.")

    # Rule 3: was the price pushed up shortly before the sale?
    recent = prices[-15:-1]                      # the two weeks before today
    spike = max(recent) if recent else 0
    raised_then_cut = spike > usual * (1 + SPIKE) and current >= usual * (1 - SAME_PRICE)
    if raised_then_cut:
        reasons.append(f"The price went up to {spike:,.0f} recently and then came back "
                       f"down to about its usual level, which makes the sale look bigger.")

    if no_real_drop or raised_then_cut:
        verdict = "Suspicious discount"
    elif never_at_original:
        verdict = "Real drop, exaggerated claim"
        reasons.append(f"The price is genuinely lower than usual ({usual:,.0f}), "
                       f"but by less than the {claimed_off}% the store claims.")
    else:
        verdict = "Genuine discount"
        reasons.append(f"Today's price is genuinely lower than its usual price "
                       f"({usual:,.0f}), and the product was sold near the original "
                       f"price before.")

    real_off = max(0, round((1 - current / usual) * 100))
    return {"verdict": verdict, "claimed_off": claimed_off, "real_off": real_off,
            "usual_price": usual, "days": days, "reasons": reasons}