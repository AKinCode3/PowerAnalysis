import streamlit as st
import math
import string
import statsmodels.stats.api as sms
from statsmodels.stats.power import NormalIndPower

# --- UI Setup ---
st.set_page_config(page_title="Conversion Power Calculator", page_icon="📈", layout="centered")
st.title("📈 A/B/n Test Power Calculator")
st.markdown("Calculate sample sizes for conversion rate metrics with dynamic traffic splits.")

# --- Sidebar: Test Parameters ---
st.sidebar.header("1. Test Parameters")

# Baseline and MDE
baseline_cvr = st.sidebar.number_input("Baseline Conversion Rate (%)", min_value=0.1, value=5.0, step=0.1) / 100
relative_mde = st.sidebar.number_input("Relative MDE (% Lift)", min_value=0.1, value=10.0, step=1.0) / 100

# Advanced Stats
st.sidebar.markdown("---")
st.sidebar.header("2. Statistical Settings")
power_input = st.sidebar.selectbox("Statistical Power", [80, 90], index=0) / 100
alpha_input = st.sidebar.selectbox("Significance Level (Alpha)", [5, 1, 10], index=0) / 100

# --- Main Page: Cell Setup & Traffic Split ---
st.subheader("3. Cell & Traffic Configuration")

# Cap total cells at 6 (1 Control + up to 5 Treatments)
num_treatments = st.number_input("Number of Treatment Cells", min_value=1, max_value=5, value=1, step=1)
total_cells = num_treatments + 1

st.markdown(f"**Traffic Split between {total_cells} cells:**")

# Generate dynamic columns for the traffic split inputs
cols = st.columns(total_cells)
cell_names = list(string.ascii_uppercase)[:total_cells] # ['A', 'B', 'C', 'D', 'E', 'F']
traffic_splits = []

# Default split (e.g., 50/50 or 33/33/33)
default_split = 100.0 / total_cells

for i, col in enumerate(cols):
    with col:
        if i == 0:
            label = f"Cell {cell_names[i]} (Control)"
        else:
            label = f"Cell {cell_names[i]} (T{i})"
            
        split = st.number_input(label, min_value=0.1, max_value=100.0, value=default_split, step=1.0, format="%.1f")
        traffic_splits.append(split / 100.0)

# Validate that traffic sums to ~100%
total_split = sum(traffic_splits)
if not math.isclose(total_split, 1.0, rel_tol=0.01):
    st.warning(f"⚠️ Your traffic splits add up to {total_split * 100:.1f}%. They should equal 100%.")

st.markdown("---")

# --- Calculation Logic ---
if st.button("Calculate Sample Size", type="primary", use_container_width=True):
    
    if math.isclose(total_split, 1.0, rel_tol=0.01):
        
        # 1. Bonferroni Correction for multiple treatments
        adjusted_alpha = alpha_input / num_treatments
        absolute_mde = baseline_cvr * relative_mde
        
        # 2. Calculate Effect Size
        effect_size = sms.proportion_effectsize(baseline_cvr, baseline_cvr + absolute_mde)
        analysis = NormalIndPower()
        
        control_weight = traffic_splits[0]
        treatment_weights = traffic_splits[1:]
        
        # 3. Find the maximum required control size across all treatments
        max_control_required = 0
        
        for t_weight in treatment_weights:
            # ratio = nobs2 / nobs1 (Treatment / Control)
            traffic_ratio = t_weight / control_weight
            
            # solve_power returns the sample size for the Control group (nobs1)
            control_size = analysis.solve_power(
                effect_size=effect_size, 
                power=power_input, 
                alpha=adjusted_alpha, 
                ratio=traffic_ratio
            )
            
            if control_size > max_control_required:
                max_control_required = control_size
                
        # 4. Extrapolate total test size based on the Control cell's requirement
        total_test_size = max_control_required / control_weight
        
        # --- Display Results ---
        st.success("Analysis Complete!")
        
        st.markdown(f"### Total Required Sample Size: **{math.ceil(total_test_size):,}** users")
        
        # Display individual cell requirements
        res_cols = st.columns(total_cells)
        for i, col in enumerate(res_cols):
            with col:
                cell_size = math.ceil(total_test_size * traffic_splits[i])
                if i == 0:
                    st.metric(label=f"Cell {cell_names[i]} (Control)", value=f"{cell_size:,}")
                else:
                    st.metric(label=f"Cell {cell_names[i]} (Treatment)", value=f"{cell_size:,}")
                    
        # Contextual notes
        with st.expander("Show Statistical Details"):
            st.write(f"- **Targeting Conversion Rate:** `{(baseline_cvr + absolute_mde)*100:.2f}%` (an absolute lift of {absolute_mde*100:.2f}%)")
            if num_treatments > 1:
                st.write(f"- **Bonferroni Adjusted Alpha:** `{adjusted_alpha:.4f}` (Original: {alpha_input})")
            else:
                st.write(f"- **Alpha:** `{alpha_input}`")
            st.write(f"- **Effect Size (Cohen's h):** `{effect_size:.4f}`")