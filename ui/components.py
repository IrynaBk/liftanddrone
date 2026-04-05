"""Reusable UI components for the dashboard."""


def stat_card(
    label: str,
    value: str,
    unit: str,
    icon: str,
    color: str,
    warning: str | None = None,
) -> str:
    """
    Create a stat card HTML component for big-number display.

    Args:
        label: Metric name (e.g., "Flight Duration")
        value: Formatted number string (e.g., "12:43")
        unit: Unit label (e.g., "mm:ss")
        icon: Emoji or symbol
        color: Hex color for value text

    Returns:
        HTML string for the stat card
    """
    return f"""
    <div style="
        background: #0f1117;
        border: 1px solid #1e2535;
        border-left: 3px solid {color};
        border-radius: 12px;
        padding: 20px 24px;
        margin: 0;
        font-family: 'IBM Plex Mono', monospace;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    ">
        <div style="
            font-size: 11px;
            color: #6b7280;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 12px;
            font-weight: 500;
        ">
            {icon}&nbsp;&nbsp;{label}
        </div>
        <div>
            <div style="
                font-size: 36px;
                font-weight: 700;
                color: {color};
                line-height: 1;
                letter-spacing: -0.02em;
                word-break: break-word;
            ">
                {value}
            </div>
            <div style="
                font-size: 12px;
                color: #9ca3af;
                margin-top: 6px;
            ">
                {unit}
            </div>
        </div>
    </div>
    """
