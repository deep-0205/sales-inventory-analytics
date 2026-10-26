import plotly.graph_objects as go
from plotly.subplots import make_subplots


def revenue_trend(trend):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(x=trend.month, y=trend.net_revenue, name="Net revenue")
    fig.add_scatter(x=trend.month, y=trend.gross_margin_pct, name="Gross margin %",
                    mode="lines+markers", secondary_y=True)
    fig.update_yaxes(title_text="Net revenue", secondary_y=False)
    fig.update_yaxes(title_text="Margin", tickformat=".0%", secondary_y=True)
    fig.update_layout(margin=dict(t=30, b=10), legend=dict(orientation="h"), hovermode="x unified")
    return fig


def pareto(abc):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(x=list(range(1, len(abc) + 1)), y=abc.net, name="Net revenue by SKU")
    fig.add_scatter(x=list(range(1, len(abc) + 1)), y=abc.cum_share, name="Cumulative share",
                    mode="lines", secondary_y=True)
    fig.update_yaxes(tickformat=".0%", secondary_y=True)
    fig.update_xaxes(title_text="SKU rank")
    return fig


def top_bottom_bar(df, value_col, label_col, title):
    fig = go.Figure(go.Bar(x=df[value_col], y=df[label_col], orientation="h"))
    fig.update_layout(title=title, yaxis=dict(autorange="reversed"), margin=dict(t=40, b=10))
    return fig