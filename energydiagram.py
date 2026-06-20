import matplotlib.pyplot as plt
import pandas as pd
import re
import argparse


def parse_connection_spec(spec):
    """
    Parses a connection specifier string.

    Supported syntax examples:
      - "2--"        → Connection to state with ID "2", dashed line, default color.
      - "4."         → Connection to state with ID "4", dotted line, default color.
      - "2blue"      → Connection to state with ID "2", solid line, color "blue".
      - "2-blue"     → Same as above.
      - "3.#454534"  → Connection to state with ID "3", dotted line, color "#454534".

    Returns a tuple: (target, linestyle, color)
    """
    spec = spec.strip()
    m = re.match(r"^(\d+)(.*)$", spec)
    if not m:
        raise ValueError(f"Cannot parse connection specifier: {spec}")

    target = m.group(1)
    mod = m.group(2).strip()  # Modifier
    color = "gray"

    if not mod:
        return target, "-", color

    if mod.startswith("."):
        if len(mod) > 1:
            color = mod[1:]
        return target, (0, (0.001, 3)), color
    if mod.startswith("--"):
        if len(mod) > 2:
            color = mod[2:]
        return target, (0, (1.5, 4)), color
    if mod.startswith("-"):
        if len(mod) > 1:
            color = mod[1:]
        return target, "-", color

    color = mod
    return target, "-", color


def plot_energy_diagram(
    data_file,
    figsize_cm=(16, 10),
    bar_width_cm=1.0,
    label_offset=0.2,
    energy_threshold=0.5,
    horizontal_sep=0.1,
    fontsize_pt=10,
    output="energy_diagram.svg",
):
    """
    Plots an energy diagram from Excel data.

    Required columns in the Excel file:
      - ID: Unique identifier of the state.
      - State: Label (if empty, no label is displayed).
      - Energy: Energy (in kcal/mol).
      - X: The x-position of the bar.
      - Connects to: Comma- or semicolon-separated connection specifiers.
      - Color: (Optional) Color of the state bar (default: black).

    Parameters:
      - label_offset: Vertical offset (in data coordinates) between the bar and the label.
                      The energy label is then placed below, and the name label above.
      - energy_threshold: Difference below which two states (at the same X) are considered "too close".
      - horizontal_sep: Horizontal offset (in data coordinates) for exactly those two states that are too close.
      - fontsize_pt: Font size of the labels.

    No axes (ticks, labels, borders) are displayed.
    """
    df = pd.read_excel(data_file)
    required_cols = ["ID", "State", "Energy", "X", "Connects to"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    if "Color" not in df.columns:
        df["Color"] = "black"
    else:
        df["Color"] = df["Color"].fillna("black")

    df["Actual X"] = df["X"].astype(float)
    df["group_x"] = df["X"].round(6)

    for group_val, group in df.groupby("group_x"):
        if len(group) >= 2:
            sorted_group = group.sort_values("Energy")
            indices = sorted_group.index.tolist()
            for i in range(len(indices) - 1):
                idx1 = indices[i]
                idx2 = indices[i + 1]
                e1 = df.loc[idx1, "Energy"]
                e2 = df.loc[idx2, "Energy"]
                if abs(e2 - e1) < energy_threshold:
                    if (
                        df.loc[idx1, "Actual X"] == group_val
                        and df.loc[idx2, "Actual X"] == group_val
                    ):
                        df.loc[idx1, "Actual X"] = float(group_val) - horizontal_sep / 2
                        df.loc[idx2, "Actual X"] = float(group_val) + horizontal_sep / 2

    state_dict = {}
    for _, row in df.iterrows():
        state_id = str(row["ID"]).strip()
        state_dict[state_id] = {
            "actual_x": row["Actual X"],
            "energy": row["Energy"],
            "state_label": row["State"],
            "color": row["Color"],
        }

    fig, ax = plt.subplots(figsize=(figsize_cm[0] / 2.54, figsize_cm[1] / 2.54))

    min_x = df["Actual X"].min()
    max_x = df["Actual X"].max()
    bar_width_data = bar_width_cm / figsize_cm[0] * (max_x - min_x)
    ax.set_xlim(min_x - bar_width_data / 2, max_x + bar_width_data / 2)

    for _, row in df.iterrows():
        if pd.notna(row["Connects to"]) and str(row["Connects to"]).strip() != "":
            targets_raw = str(row["Connects to"]).replace(";", ",")
            connection_specs = [
                s.strip() for s in targets_raw.split(",") if s.strip() != ""
            ]
            start_x = row["Actual X"] + bar_width_data / 2
            start_y = row["Energy"]
            for spec in connection_specs:
                try:
                    target, linestyle, conn_color = parse_connection_spec(spec)
                except ValueError as e:
                    print(e)
                    continue
                if target not in state_dict:
                    print(f"Warning: target ID {target} not found.")
                    continue
                target_info = state_dict[target]
                end_x = target_info["actual_x"] - bar_width_data / 2
                end_y = target_info["energy"]
                conn_line = ax.plot(
                    [start_x, end_x],
                    [start_y, end_y],
                    color=conn_color,
                    linestyle=linestyle,
                    linewidth=1,
                    antialiased=True,
                )[0]
                try:
                    conn_line.set_dash_capstyle("round")
                except Exception as ex:
                    print("Could not set dash cap style:", ex)

    state_lines = []
    for _, row in df.iterrows():
        x_center = row["Actual X"]
        energy = row["Energy"]
        color = row["Color"]
        x_left = x_center - bar_width_data / 2
        x_right = x_center + bar_width_data / 2

        bar_line = ax.plot(
            [x_left, x_right],
            [energy, energy],
            color=color,
            linewidth=1.5,
            antialiased=True,
        )[0]
        bar_line.set_solid_capstyle("round")
        state_lines.append(bar_line)

    for _, row in df.iterrows():
        x_center = row["Actual X"]
        energy = row["Energy"]
        color = row["Color"]
        # Energie-Label fix unterhalb des Balkens
        ax.text(
            x_center,
            energy - label_offset,
            f"{energy:.1f}",
            ha="center",
            va="top",
            fontsize=fontsize_pt,
            color=color,
            transform=ax.transData,
        )
        # Name-Label fix
        if pd.notna(row["State"]) and str(row["State"]).strip() != "":
            ax.text(
                x_center,
                energy + label_offset,
                f"{row['State']}",
                ha="center",
                va="bottom",
                fontsize=fontsize_pt,
                color=color,
                transform=ax.transData,
            )

    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.tight_layout()
    plt.savefig(output, dpi=300)
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="EnergyDiagram",
        description="Plot a energy graph based on xlsx data.",
        usage="%(prog)s [options]",
        epilog="'Text at the bottom of the help.'",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        default="data.xlsx",
        help="Excel file name, default: 'data.xlsx'",
        required=False,
    )
    parser.add_argument(
        "--width",
        type=float,
        default=16,
        help="Figure width in cm, default: '16'",
        required=False,
    )
    parser.add_argument(
        "--height",
        type=float,
        default=10,
        help="Figure width in cm, default: '10'",
        required=False,
    )
    parser.add_argument(
        "-b",
        "--bar_width",
        type=float,
        default=1,
        help="Width of the bars in cm, default: '1'",
        required=False,
    )
    parser.add_argument(
        "-o",
        "--offset",
        type=float,
        default=0.5,
        help="Vertical offset (in data coordinates) between the bar and the label. The energy label is then placed below, and the name label above. Default: '0.5'",
        required=False,
    )
    parser.add_argument(
        "-e",
        "--threshold",
        type=float,
        default=1,
        help="Difference below which two states (at the same X) are considered 'too close'. Default: 1",
        required=False,
    )
    parser.add_argument(
        "-s",
        "--fontsize",
        type=float,
        default=8,
        help="Font size of the labels. Default: 8",
        required=False,
    )
    parser.add_argument(
        "-d",
        "--distance",
        type=float,
        default=0.2,
        help="Horizontal offset (in data coordinates) for exactly those two states that are too close. Default: '0.2'",
        required=False,
    )
    parser.add_argument(
        "--output",
        type=str,
        default="energy_diagram.svg",
        help="Output file name.",
        required=False,
    )

    args = parser.parse_args()

    plot_energy_diagram(
        args.file,
        figsize_cm=(args.width, args.height),
        bar_width_cm=args.bar_width,
        label_offset=args.offset,
        energy_threshold=args.threshold,
        horizontal_sep=args.distance,
        fontsize_pt=args.fontsize,
        output=args.output,
    )
