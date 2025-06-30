import streamlit as st
import pandas as pd
from ortools.sat.python import cp_model

st.set_page_config(page_title="Tube Cutting Optimizer", layout="wide")

# Title
st.title("Tube Cutting Optimization Tool")

# Upload section
uploaded_file = st.file_uploader("Upload today's demand CSV", type=["csv"])

if uploaded_file:
    try:
        # Read uploaded file
        df = pd.read_csv(uploaded_file)
        st.success("Demand file uploaded successfully!")

        st.markdown("###  Input Demand Data:")
        st.dataframe(df, use_container_width=True)

        # Prepare for processing
        df = df.sort_values(by=["Thickness (mm)", "Diameter (mm)", "Required Length (mm)"], ascending=[True, True, False])

        final_plans = []

        # Group by Thickness and Diameter
        for (thickness, diameter), group in df.groupby(["Thickness (mm)", "Diameter (mm)"]):
            group = group.reset_index(drop=True)
            lengths = group["Required Length (mm)"].tolist()
            demands = group["Demand"].tolist()
            standard_length = group["Standard Tube Length (mm)"].iloc[0]

            # OR-Tools Cutting Stock Model
            model = cp_model.CpModel()

            num_lengths = len(lengths)
            max_tubes = sum(demands)

            x = {}
            for i in range(max_tubes):
                for j in range(num_lengths):
                    x[(i, j)] = model.NewIntVar(0, demands[j], f'x_{i}_{j}')

            used = [model.NewBoolVar(f'used_{i}') for i in range(max_tubes)]

            for j in range(num_lengths):
                model.Add(sum(x[(i, j)] for i in range(max_tubes)) == demands[j])

            for i in range(max_tubes):
                model.Add(sum(x[(i, j)] * lengths[j] for j in range(num_lengths)) <= standard_length).OnlyEnforceIf(used[i])
                model.Add(sum(x[(i, j)] * lengths[j] for j in range(num_lengths)) == 0).OnlyEnforceIf(used[i].Not())

            model.Minimize(sum(used))

            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 30.0
            status = solver.Solve(model)

            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                for i in range(max_tubes):
                    if solver.Value(used[i]):
                        plan = []
                        total_used = 0
                        for j in range(num_lengths):
                            num_pieces = solver.Value(x[(i, j)])
                            if num_pieces > 0:
                                plan.append(f"{num_pieces} x {lengths[j]}mm")
                                total_used += num_pieces * lengths[j]

                        scrap = standard_length - total_used
                        final_plans.append({
                            "Raw Tube Length": standard_length,
                            "Cut Plan": " + ".join(plan),
                            "Scrap (mm)": scrap
                        })
            else:
                st.warning(f"No feasible solution found for Thickness {thickness} mm and Diameter {diameter} mm.")

        if final_plans:
            output = pd.DataFrame(final_plans)
            st.markdown("### Optimized Cutting Plan:")
            st.dataframe(output, use_container_width=True)

            csv = output.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Cutting Plan",
                data=csv,
                file_name='cutting_plan.csv',
                mime='text/csv'
            )
        else:
            st.warning("No feasible solutions found for any group.")

    except Exception as e:
        st.error(f"Error processing file: {e}")

else:
    st.info("Please upload a CSV file with columns: Required Length (mm), Thickness (mm), Diameter (mm), Demand, Standard Tube Length (mm)")

# Footer
st.markdown("---")
st.caption("© 2025 TubeCut AI | Built with using Streamlit")



