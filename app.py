# gir_calculator_auto_pick.py
import streamlit as st

st.set_page_config(page_title="GIR Calculator", layout="centered")
st.title("Dextrose Calculator — GIR Calculator")
st.markdown(
    "Enter patient weight (grams), glucose volume (mL/day) and target GIR (mg/kg/min). "
    "Press **Calculate** to compute the required dextrose % and a two-stock mixing instruction."
)

# -----------------------
# Helpers
# -----------------------
def percent_needed_for_target_gir(target_gir_mgkgmin, weight_kg, total_volume_ml):
    """ percent (%) = GIR * weight_kg * 144 / volume_ml """
    if weight_kg <= 0 or total_volume_ml <= 0:
        return None
    return target_gir_mgkgmin * weight_kg * 144.0 / total_volume_ml

def mix_two_solutions(percent1, percent2, final_percent, final_volume_ml):
    """ returns (v1_ml, v2_ml) for volumes of stock1 and stock2 """
    if final_volume_ml <= 0 or percent1 == percent2:
        return None, None
    v1 = final_volume_ml * (final_percent - percent2) / (percent1 - percent2)
    v2 = final_volume_ml - v1
    return v1, v2

def safety_message_for_percent(pct):
    """Return (level, message, emoji)"""
    if pct is None:
        return ("invalid", "Invalid percent", "⚪")
    if pct <= 12.5:
        return ("safe", "Safe for peripheral infusion ✅", "✅")
    elif pct <= 20.0:
        return ("caution", "Caution — prefer central line if prolonged usage ⚠️", "⚠️")
    else:
        return ("unsafe", "Recommend central line ", "")

def auto_pick_stocks(target_pct, stock_list):
    """
    Pick two stocks such that one <= target and one >= target.
    Picks nearest lower and nearest higher. Returns (lower_stock, higher_stock).
    If target is below smallest stock return (None, smallest). If above largest return (largest, None).
    """
    sorted_stocks = sorted(stock_list)
    lower = None
    higher = None
    for s in sorted_stocks:
        if s <= target_pct:
            lower = s
        if s >= target_pct and higher is None:
            higher = s
    if lower is None and higher is not None:
        return None, higher
    if higher is None and lower is not None:
        return lower, None
    return lower, higher

# -----------------------
# Session defaults
# -----------------------
if "manual_stock_edit" not in st.session_state:
    st.session_state.manual_stock_edit = False
if "last_final_percent" not in st.session_state:
    st.session_state.last_final_percent = None
if "last_stock_a" not in st.session_state:
    st.session_state.last_stock_a = 0.0
if "last_stock_b" not in st.session_state:
    st.session_state.last_stock_b = 10.0
if "calculated" not in st.session_state:
    st.session_state.calculated = False

# -----------------------
# Inputs (with increments)
# -----------------------
st.header("Patient inputs")
col1, col2, col3 = st.columns([1.2, 1, 1])
with col1:
    weight_g = st.number_input("Patient weight (grams)", min_value=1.0, value=1850.0, format="%.0f")
with col2:
    # step = 5 for glucose volume increments
    glu_volume_ml = st.number_input("Glucose volume (mL/day)", min_value=1.0, value=220.0, step=5.0, format="%.0f")
with col3:
    # step = 0.5 for target GIR increments
    target_gir = st.number_input("Target GIR (mg/kg/min)", min_value=0.0, value=6.0, step=0.5, format="%.2f")

st.write("---")

# stock options (user can edit after results via toggle)
stock_options = [0.0, 5.0, 10.0, 25.0, 50.0]

# Checkbox toggle: allow user to manually edit stocks AFTER auto-pick
st.session_state.manual_stock_edit = st.checkbox("Edit stock choices manually after calculation", value=False)

st.write("---")
calc_btn = st.button("Calculate")

# -----------------------
# Calculation logic
# -----------------------
if calc_btn:
    weight_kg = weight_g / 1000.0
    st.session_state.calculated = False
    if weight_kg <= 0 or glu_volume_ml <= 0:
        st.error("Enter valid positive weight and glucose volume.")
    else:
        final_percent = percent_needed_for_target_gir(target_gir, weight_kg, glu_volume_ml)
        if final_percent is None:
            st.error("Couldn't compute required percent — check inputs.")
        else:
            # Auto-pick stocks to bracket the target by default
            lower, higher = auto_pick_stocks(final_percent, stock_options)
            # Determine chosen A and B based on auto-pick result
            if lower is None and higher is None:
                # no stock options present (shouldn't happen)
                stock_a, stock_b = 0.0, 10.0
                st.warning("No stock options available; using defaults 0% and 10%.")
            elif lower is None:
                # target below smallest stock -> use 0% and smallest higher
                stock_a, stock_b = 0.0, higher
                st.warning(f"Target {final_percent:.2f}% is below smallest available stock ({higher:.1f}%). Using 0% & {higher:.1f}%.")
            elif higher is None:
                # target above largest -> use largest lower and 50%
                stock_a, stock_b = lower, 50.0
                st.warning(f"Target {final_percent:.2f}% is above largest available stock ({lower:.1f}%). Using {lower:.1f}% & 50%.")
            else:
                # normal case: use lower and higher
                # if exact match (lower == higher) pick that and a neighbor where possible
                if abs(lower - higher) < 1e-9:
                    idx = stock_options.index(lower)
                    if idx == 0:
                        stock_a, stock_b = stock_options[0], stock_options[1]
                    else:
                        stock_a, stock_b = stock_options[idx-1], stock_options[idx]
                else:
                    stock_a, stock_b = lower, higher

            # store in session for later editing
            st.session_state.last_final_percent = final_percent
            st.session_state.last_stock_a = float(stock_a)
            st.session_state.last_stock_b = float(stock_b)
            st.session_state.calculated = True

# -----------------------
# Results display (combined, mixing instruction included in result)
# -----------------------
if st.session_state.calculated and st.session_state.last_final_percent is not None:
    final_percent = st.session_state.last_final_percent
    stock_a = st.session_state.last_stock_a
    stock_b = st.session_state.last_stock_b
    final_volume_input = glu_volume_ml  # internal use; not shown as separate "final volume" input in results

    # top-level result summary (includes the mixing instruction, not labeled separately)
    st.subheader("Result")
    st.markdown(f"- Required dextrose concentration: **{final_percent:.2f}%**")
    st.markdown(f"- Patient: **{weight_g:.0f} g**  •  Glucose volume/day: **{glu_volume_ml:.0f} mL**  •  Target GIR: **{target_gir:.2f} mg/kg/min**")

    # safety message
    level, msg, emoji = safety_message_for_percent(final_percent)
    if level == "safe":
        st.success(f"{emoji}  {msg}")
    elif level == "caution":
        st.warning(f"{emoji}  {msg}")
    else:
        st.error(f"{emoji}  {msg}")

    st.write("")  # spacer

    # If user opted to manually edit stocks, show selectboxes; else show the auto-picked stocks (but allow changing via checkbox)
    if st.session_state.manual_stock_edit:
        col1, col2 = st.columns([1, 1])
        with col1:
            stock_a = st.selectbox("Solution A (%)", stock_options, index=stock_options.index(stock_a) if stock_a in stock_options else 0)
        with col2:
            stock_b = st.selectbox("Solution B (%)", stock_options, index=stock_options.index(stock_b) if stock_b in stock_options else 1)
        # update session state with user picks
        st.session_state.last_stock_a = float(stock_a)
        st.session_state.last_stock_b = float(stock_b)
    else:
        # show auto-picked stocks as info (user can toggle the checkbox to edit)
        st.info(f"Auto-picked stocks: Solution A = **{stock_a:.1f}%**, Solution B = **{stock_b:.1f}%**. (Enable 'Edit stock choices manually' to change.)")

    # compute mixing using currently selected stocks
    a = float(st.session_state.last_stock_a)
    b = float(st.session_state.last_stock_b)

    if a == b:
        # if exactly equal and equal to final_percent -> use directly
        if abs(final_percent - a) < 1e-6:
            st.markdown(f"Use **{a:.1f}%** stock directly — no mixing required.")
        else:
            st.warning(f"Selected stocks are identical ({a:.1f}%). Choose two different stocks that bracket the target or enable manual edit.")
    else:
        v1, v2 = mix_two_solutions(a, b, final_percent, final_volume_input)
        if v1 is None or v2 is None:
            st.error("Unable to calculate mixture with chosen stocks.")
        else:
            if v1 < -1e-6 or v2 < -1e-6:
                st.error(
                    "Target concentration is outside the range of chosen stocks. "
                    "The target must be between the two stock concentrations (one higher, one lower)."
                )
                st.write(f"Selected: A={a}%, B={b}%. Target: {final_percent:.2f}%.")
            else:
                v1 = max(0.0, v1)
                v2 = max(0.0, v2)
                # The mixing instruction is part of the Result — no separate "mixing suggestion" heading
                st.markdown(
                    f"Mix **{v1:.1f} mL** of Solution A (**{a:.1f}%**) with **{v2:.1f} mL** of Solution B (**{b:.1f}%**) "
                    f"to obtain **{final_volume_input:.0f} mL** of **{final_percent:.2f}%** — this achieves a GIR of **{target_gir:.2f} mg/kg/min**."
                )

    # concise details
    st.write("---")
    grams_needed_per_day = (final_percent / 100.0) * glu_volume_ml
    st.write(f"- Dextrose required per day: **{grams_needed_per_day:.2f} g**")
    st.write(f"- Formula used: percent (%) = GIR × weight(kg) × 144 / volume(mL/day)")
    st.caption("⚠️ This calculator is an aid only. Confirm compounding technique, sterility and local policy before administration.")

else:
    st.info("Enter inputs and press **Calculate** to get result (auto-picks stocks by default).")
