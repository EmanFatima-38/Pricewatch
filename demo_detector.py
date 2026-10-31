from src.analysis import check_discount

examples = {
    "Always on 'sale' (same price every day)": [(5999, 18999)] * 10,
    "Real sale": [(10000, None)] * 8 + [(7000, 10000)],
    "Price raised before the sale": [(5000, None)] * 10 + [(7000, None)] * 3 + [(5000, 8000)],
    "Real drop, but exaggerated": [(6000, None)] * 8 + [(5000, 18999)],
}

for title, history in examples.items():
    result = check_discount(history)
    print(f"\n{title}\n  -> {result['verdict']}")
    for reason in result["reasons"]:
        print(f"     - {reason}")