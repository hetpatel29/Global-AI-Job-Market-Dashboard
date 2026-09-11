from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_plotly

APP_DIR = Path(__file__).resolve().parent
DATA_JOBS = APP_DIR / "data" / "master_jobs.csv"
DATA_COUNTRY_TRENDS = APP_DIR / "data" / "country_ai_trends.csv"

PLOT_TEMPLATE = "plotly_white"
FONT = "DM Sans, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
HIGHLIGHT = "#f97316"
YEAR_MIN, YEAR_MAX = 2020, 2026
PLOT_H = 460

SKILL_COLORS = {"Programming": "#3b82f6", "ML": "#f97316", "Cloud": "#22c55e", "Unknown": "#94a3b8"}
ROLE_COLORS = {"Engineering": "#3b82f6","Analytics": "#f97316","Research": "#22c55e","Product": "#ef4444","Leadership": "#a855f7",}
EXTRA_COLORS = ["#ec4899", "#14b8a6", "#eab308", "#6366f1", "#84cc16"]


def color_map(base, extra, keys):
    out = dict(base)
    for i, k in enumerate(keys):
        out.setdefault(k, extra[i % len(extra)])
    return {k: out[k] for k in keys}


def role_cmap(roles):
    return color_map(ROLE_COLORS, EXTRA_COLORS, roles)


def skill_cmap(categories):
    return color_map(SKILL_COLORS, EXTRA_COLORS, categories)


def fmt(val, prefix="", suffix=""):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    return f"{prefix}{val:,.0f}{suffix}"


def empty_fig(msg):
    fig = go.Figure()
    fig.update_layout(
        template=PLOT_TEMPLATE,
        height=PLOT_H,
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(t=60, r=20, b=28, l=20),
        annotations=[dict(
            text=msg, x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(size=15, color="#9ca3af")
        )],
    )
    return fig


def layout(fig, title, xtitle=None, ytitle=None, height=PLOT_H, legend=True, legend_right=True):
    mr = 150 if (legend and legend_right) else 24
    fig.update_layout(
    title=dict(text=title, x=0.5, xanchor="center", font=dict(size=18, family=FONT, color="#111827")),
    template=PLOT_TEMPLATE,
    height=height,
    showlegend=legend,
    margin=dict(t=62, r=mr, b=52, l=62),
    font=dict(family=FONT, size=12, color="#374151"),
    paper_bgcolor="white",
    plot_bgcolor="white",
    legend=dict(orientation="v",x=1.02,y=0.5,xanchor="left",yanchor="middle",font=dict(size=11),) if legend and legend_right else {},
    )
    axis_kw = dict(font=dict(size=12, family=FONT, color="#374151"))
    fig.update_xaxes(showgrid=False,linecolor="rgba(0,0,0,0.1)",zeroline=False,title=dict(text=xtitle, **axis_kw) if xtitle else None,tickfont=dict(size=11),)
    fig.update_yaxes(gridcolor="rgba(0,0,0,0.07)",linecolor="rgba(0,0,0,0.1)",zeroline=False,title=dict(text=ytitle, **axis_kw) if ytitle else None,tickfont=dict(size=11),)
    return fig

def emphasize(fig, selected):
    if not selected:
        return fig
    for tr in fig.data:
        if not hasattr(tr, "name") or tr.type != "scatter":
            continue
        if tr.name in selected:
            tr.update(line=dict(width=3.5), opacity=1, marker=dict(size=7))
        else:
            tr.update(line=dict(width=1.5), opacity=0.3, marker=dict(size=4))
    return fig


def add_end_labels(fig, df, x, y, group):
    last = df.sort_values(x).groupby(group, as_index=False).tail(1)
    if len(last) > 8:
        return fig
    for _, row in last.iterrows():
        fig.add_annotation(
            x=row[x], y=row[y], xref="x", yref="y", text=str(row[group]),
            showarrow=False, xshift=7, align="left",
            font=dict(size=10, color="#374151"),
        )
    return fig


def build_top_skills(skills_df, n=15):
    df = skills_df[~skills_df["skill"].isin(["Unknown", "None", "nan"])].copy()
    if df.empty:
        return pd.DataFrame()
    counts = df.groupby("skill")["job_id"].nunique().sort_values(ascending=False).head(n)
    rows = []
    for s in counts.index:
        mode_vals = df.loc[df["skill"] == s, "skill_category"].mode()
        rows.append({
            "skill": s,
            "job_count": int(counts[s]),
            "skill_category": str(mode_vals.iloc[0]) if len(mode_vals) else "Unknown",
        })
    return pd.DataFrame(rows).sort_values("job_count", ascending=True)


def load_jobs():
    df = pd.read_csv(DATA_JOBS)
    for col in ["job_id", "country", "role_category", "experience_level", "remote_type", "skill", "skill_category", "standardized_title"]:
        df[col] = df[col].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")
    for col in ["posted_year", "salary_max_usd", "salary_min_usd", "min_experience_years"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df[df["posted_year"].notna()].copy()
    df["posted_year"] = df["posted_year"].astype(int).clip(YEAR_MIN, YEAR_MAX)
    return df


def load_trends():
    t = pd.read_csv(DATA_COUNTRY_TRENDS)
    t["year"] = pd.to_numeric(t["year"], errors="coerce").astype("Int64")
    return t.dropna(subset=["year", "country"]).assign(year=lambda d: d["year"].astype(int))


raw_df = load_jobs()
jobs_df = raw_df.drop_duplicates("job_id").copy()
trends_df = load_trends()

country_choices = sorted(c for c in jobs_df["country"].unique() if c != "Unknown")
role_choices = sorted(r for r in jobs_df["role_category"].unique() if r != "Unknown")
exp_choices = [l for l in ["Entry", "Mid", "Senior"] if l in jobs_df["experience_level"].unique()]
trend_countries = sorted(c for c in trends_df["country"].dropna().unique() if c != "Unknown")
trend_default = next((c for c in ("United States", *trend_countries)), None)

sal = jobs_df["salary_max_usd"].dropna()
SAL_MIN = int(sal.min()) if not sal.empty else 0
SAL_MAX = int(sal.max()) if not sal.empty else 300_000


@reactive.calc
def filtered_jobs():
    f = raw_df
    if sel := set(input.countries()):
        f = f[f["country"].isin(sel)]
    if sel := set(input.roles()):
        f = f[f["role_category"].isin(sel)]
    if sel := set(input.exp()):
        f = f[f["experience_level"].isin(sel)]
    y0, y1 = input.year_range()
    s0, s1 = input.salary_range()
    return f[f["posted_year"].between(y0, y1) & f["salary_max_usd"].between(s0, s1)].copy()


@reactive.calc
def unique_jobs():
    df = filtered_jobs()
    return df.drop_duplicates("job_id").copy() if not df.empty else df


@reactive.calc
def filtered_trends():
    y0, y1 = input.year_range()
    sel = set(input.countries())
    t = trends_df[trends_df["year"].between(y0, y1)]
    return t[t["country"].isin(sel)].copy() if sel else t.iloc[0:0].copy()


CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');
:root { --bg:#f0f4f8; --surface:#ffffff; --border:rgba(0,0,0,0.07); --text:#111827; --muted:#6b7280; --accent:#f97316; --radius:14px; --shadow:0 2px 12px rgba(0,0,0,0.06); }
body { background:var(--bg); color:var(--text); font-family:'DM Sans', -apple-system, sans-serif; }
.bslib-sidebar-layout > .sidebar { background:var(--surface); border-right:1px solid var(--border); padding:1.25rem 1rem 1.5rem; min-width:260px; max-width:280px; }
.sidebar h4 { font-size:1rem; font-weight:700; letter-spacing:.02em; color:var(--text); margin:0 0 1rem; }
.filter-group { padding-bottom:1.1rem; margin-bottom:1.1rem; border-bottom:1px solid var(--border); }
.filter-group:last-child { border-bottom:none; margin-bottom:0; padding-bottom:0; }
.filter-group .shiny-input-container { margin-bottom:0 !important; }
.filter-group label.control-label { display:block; font-size:.72rem; font-weight:700; letter-spacing:.07em; text-transform:uppercase; color:var(--muted); margin-bottom:.55rem; }
.filter-group .shiny-input-checkboxgroup .checkbox { margin-bottom:5px; }
.filter-group .shiny-input-checkboxgroup label { font-size:.88rem; }
.filter-group .irs--shiny .irs-bar { background:var(--accent); }
.filter-group .irs--shiny .irs-handle { border-color:var(--accent); }
.app-shell { padding:1.25rem 1.5rem 2.5rem; max-width:1280px; margin:0 auto; width:100%; box-sizing:border-box; }
.module-card { background:var(--surface); border-radius:var(--radius); box-shadow:var(--shadow); border:none !important; padding:20px; margin-bottom:1.1rem; }
.module-card .card-body { padding:0; }
.value-card { background:var(--surface); border-radius:var(--radius); box-shadow:var(--shadow); border:none !important; padding:16px 18px; min-height:96px; }
.vc-label { font-size:.72rem; font-weight:700; letter-spacing:.07em; text-transform:uppercase; color:var(--muted); }
.vc-value { font-size:1.75rem; font-weight:700; line-height:1.15; color:var(--text); margin-top:.2rem; }
.vc-note { font-size:.78rem; color:var(--muted); margin-top:.25rem; }
.bslib-navs-tab-content { padding:0 !important; }
.nav-tabs .nav-link { font-size:.875rem; font-weight:500; color:var(--muted); }
.nav-tabs .nav-link.active { color:var(--text); font-weight:600; }
.module-card .plotly { width:100% !important; }
"""

ui.page_opts(title="Global AI Job Market", fillable=True)
ui.tags.style(CUSTOM_CSS)

with ui.sidebar(open="desktop"):
    ui.h4("Filters")
    with ui.div(class_="filter-group"):
        ui.input_checkbox_group("countries", "Country", choices=country_choices, selected=["India", "USA", "UK", "Germany","Canada","Australia"])
    with ui.div(class_="filter-group"):
        ui.input_checkbox_group("roles", "Role Category", choices=role_choices, selected=["Engineering", "Analytics"])
    with ui.div(class_="filter-group"):
        ui.input_slider("year_range", "Year Range", min=YEAR_MIN, max=YEAR_MAX, value=(YEAR_MIN, YEAR_MAX), step=1, sep="")
    with ui.div(class_="filter-group"):
        ui.input_checkbox_group("exp", "Experience Level", choices=exp_choices, selected=["Entry","Mid","Senior"])
    with ui.div(class_="filter-group"):
        ui.input_slider("salary_range", "Salary Range (USD)", min=SAL_MIN, max=SAL_MAX, value=(SAL_MIN, SAL_MAX), step=1000, sep=",")

with ui.div(class_="app-shell"):
    with ui.navset_tab(id="tabs"):
        with ui.nav_panel("Home"):
            with ui.layout_columns(col_widths=(3, 3, 3, 3), gap="1rem"):
                with ui.card(class_="value-card"):
                    ui.div("Total Jobs", class_="vc-label")
                    @render.ui
                    def kpi_jobs():
                        return ui.div(fmt(len(unique_jobs())), class_="vc-value")
                    ui.p("Unique postings", class_="vc-note")

                with ui.card(class_="value-card"):
                    ui.div("Avg. Salary", class_="vc-label")
                    @render.ui
                    def kpi_salary():
                        return ui.div(fmt(unique_jobs()["salary_max_usd"].mean(), "$"), class_="vc-value")
                    ui.p("Mean max salary (USD)", class_="vc-note")

                with ui.card(class_="value-card"):
                    ui.div("Remote Share", class_="vc-label")
                    @render.ui
                    def kpi_remote():
                        j = unique_jobs()
                        v = fmt(j["remote_type"].eq("Remote").mean() * 100, suffix="%") if not j.empty else "—"
                        return ui.div(v, class_="vc-value")
                    ui.p("Fully remote roles", class_="vc-note")

                with ui.card(class_="value-card"):
                    ui.div("Countries", class_="vc-label")
                    @render.ui
                    def kpi_ctry():
                        return ui.div(fmt(unique_jobs()["country"].nunique()), class_="vc-value")
                    ui.p("Distinct countries", class_="vc-note")

            with ui.card(class_="module-card", full_screen=True):
                @render_plotly
                def salary_trend_hero():
                    t = filtered_trends()
                    sel = set(list(input.countries())[:6])
                    if t.empty or not sel:
                        return empty_fig("Select at least one country.")
                    fig = px.line(t, x="year", y="avg_salary_usd", color="country", markers=True, template=PLOT_TEMPLATE, color_discrete_sequence=px.colors.qualitative.Safe)
                    fig.update_yaxes(tickprefix="$")
                    fig.update_xaxes(dtick=1)
                    fig = emphasize(fig, sel)
                    for tr in fig.data:
                        if "lines" in str(getattr(tr, "mode", "")):
                            tr.hovertemplate = "$%{y:,.0f}<extra></extra>"
                    return layout(fig, "Average Salary by Country", xtitle="Year", ytitle="Average Salary (USD)")

            with ui.card(class_="module-card", full_screen=True):
                @render_plotly
                def remote_work_trend():
                    t = filtered_trends()
                    sel = set(list(input.countries())[:6])
                    if t.empty or not sel:
                        return empty_fig("Select at least one country.")
                    fig = px.line(t, x="year", y="remote_percentage", color="country", markers=True, template=PLOT_TEMPLATE, color_discrete_sequence=px.colors.qualitative.Safe)
                    fig.update_yaxes(ticksuffix="%", range=[0, 100])
                    fig.update_xaxes(dtick=1)
                    fig.add_vline(x=2020, line_width=1, line_dash="dash", line_color=HIGHLIGHT, opacity=0.8)
                    fig.add_annotation(x=2020, y=1, xref="x", yref="paper", text="2020 reference", showarrow=False, yshift=8, font=dict(size=10, color=HIGHLIGHT))
                    fig = emphasize(fig, sel)
                    for tr in fig.data:
                        if "lines" in str(getattr(tr, "mode", "")):
                            tr.hovertemplate = "%{y:.1f}%<extra></extra>"
                    return layout(fig, "Remote Work Share by Country", xtitle="Year", ytitle="Remote Job Share (%)")

            with ui.card(class_="module-card", full_screen=True):
                @render_plotly
                def global_salary_trend():
                    t = filtered_trends()
                    if t.empty:
                        return empty_fig("No data for selected filters.")
                    fig = px.line(t, x="year", y="avg_salary_usd", color="country", markers=True, template=PLOT_TEMPLATE, color_discrete_sequence=px.colors.qualitative.Safe)
                    fig.update_yaxes(tickprefix="$")
                    fig.update_xaxes(dtick=1)
                    fig = emphasize(fig, set(list(input.countries())[:6]))
                    for tr in fig.data:
                        if "lines" in str(getattr(tr, "mode", "")):
                            tr.hovertemplate = "$%{y:,.0f}<extra></extra>"
                    return layout(fig, "Global Salary Trends Comparison", xtitle="Year", ytitle="Average Salary (USD)")

        with ui.nav_panel("Salary Analytics"):
            with ui.card(class_="module-card", full_screen=True):
                @render_plotly
                def salary_distribution():
                    df = unique_jobs().dropna(subset=["salary_max_usd", "role_category"])
                    if df.empty:
                        return empty_fig("No salary data for these filters.")
                    order = df.groupby("role_category")["salary_max_usd"].median().sort_values(ascending=False).index.tolist()
                    fig = px.box(df, x="role_category", y="salary_max_usd", color="role_category", points="outliers", color_discrete_map=role_cmap(order), category_orders={"role_category": order}, template=PLOT_TEMPLATE)
                    fig.update_layout(showlegend=False)
                    fig.update_traces(hovertemplate="$%{y:,.0f}<extra></extra>", selector=dict(type="box"))
                    fig.update_yaxes(tickprefix="$")
                    return layout(fig, "Salary Distribution by Role", xtitle="Role Category", ytitle="Salary (USD)", legend=False)

            with ui.card(class_="module-card", full_screen=True):
                @render_plotly
                def experience_salary_scatter():
                    df = unique_jobs().dropna(subset=["min_experience_years", "salary_max_usd", "role_category"])
                    df = df[df["role_category"].isin(["Analytics", "Engineering"])]
                    if len(df) < 8:
                        return empty_fig("Not enough data to plot.")
                    if len(df) > 4000:
                        df = df.sample(4000, random_state=42)
                    fig = px.scatter(df,x="min_experience_years",y="salary_max_usd",facet_col="role_category",facet_col_spacing=0.14,color="role_category",color_discrete_map=role_cmap(["Analytics", "Engineering"]),opacity=0.55,template=PLOT_TEMPLATE,height=500,)
                    for role, color in [("Analytics", "#f97316"), ("Engineering", "#3b82f6")]:
                        sub = df[df["role_category"] == role].sort_values("min_experience_years")
                        x = sub["min_experience_years"].to_numpy()
                        y = sub["salary_max_usd"].to_numpy()
                        mask = np.isfinite(x) & np.isfinite(y)
                        if mask.sum() > 2:
                            m, b = np.polyfit(x[mask], y[mask], 1)
                            xs = np.linspace(x[mask].min(), x[mask].max(), 80)
                            fig.add_trace(
                                go.Scatter(x=xs,y=m * xs + b,mode="lines",line=dict(color=color, width=3),name=f"{role} trend",showlegend=False,hoverinfo="skip",),
                                row=1,
                                col=1 if role == "Analytics" else 2,)
                    fig.update_traces(marker=dict(size=8, line=dict(width=0)), hovertemplate="$%{y:,.0f}<extra></extra>")
                    fig.update_yaxes(tickprefix="$", matches=None)
                    fig.update_xaxes(title="Min. Experience (Years)")
                    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
                    return layout(fig, "Experience vs Salary", xtitle="Min. Experience (Years)", ytitle="Max Salary (USD)", legend=False, legend_right=False)

            with ui.card(class_="module-card", full_screen=True):
                @render_plotly
                def role_mean_salary_bar():
                    df = unique_jobs()
                    if df.empty:
                        return empty_fig("No jobs for these filters.")
                    g = df.groupby("role_category", as_index=False)["salary_max_usd"].mean().sort_values("salary_max_usd", ascending=False)
                    fig = px.bar(g, x="role_category", y="salary_max_usd", color="role_category", color_discrete_map=role_cmap(g["role_category"].tolist()), template=PLOT_TEMPLATE)
                    fig.update_layout(showlegend=False)
                    fig.update_traces(hovertemplate="$%{y:,.0f}<extra></extra>")
                    fig.update_yaxes(tickprefix="$")
                    return layout(fig, "Mean Max Salary by Role", xtitle="Role", ytitle="Mean Max Salary (USD)", legend=False)

        with ui.nav_panel("Country Trend"):
            with ui.card(class_="module-card", full_screen=True):
                @render_plotly
                def country_salary_trend():
                    y0, y1 = input.year_range()
                    sel = set(input.countries())

                    t = trends_df[trends_df["year"].between(y0, y1) & trends_df["country"].isin(sel)].copy()

                    if t.empty:
                        return empty_fig("No trend data for this selection.")

                    order = [c for c in ["India", "United States", "United Kingdom", "Germany", "Canada", "Australia"] if c in t["country"].unique()]
                    if not order:
                        order = sorted(t["country"].unique().tolist())

                    fig = px.line(t,x="year",y="avg_salary_usd",color="country",facet_col="country",facet_col_wrap=3,facet_col_spacing=0.08,facet_row_spacing=0.10,markers=True,template=PLOT_TEMPLATE,color_discrete_sequence=px.colors.qualitative.Safe,category_orders={"country": order},height=550,)

                    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
                    fig.update_traces(line=dict(width=2.5),marker=dict(size=7),hovertemplate="$%{y:,.0f}<extra></extra>",showlegend=False,)

                    ymax = t["avg_salary_usd"].max()
                    fig.update_yaxes(tickprefix="$", range=[0, ymax * 1.05], matches=None)
                    fig.update_xaxes(dtick=1)

                    return layout(fig,"Average Salary by Country",xtitle="Year",ytitle="Average Salary (USD)",legend=False,legend_right=False,height=550,)

        with ui.nav_panel("Skills & Roles"):
            with ui.card(class_="module-card", full_screen=True):
                @render_plotly
                def top_skills_chart():
                    df = filtered_jobs()
                    if df.empty:
                        return empty_fig("No skill data for these filters.")
                    top = build_top_skills(df[df["skill"].notna()])
                    if top.empty:
                        return empty_fig("No skills to rank.")
                    cats = top["skill_category"].unique().tolist()
                    fig = px.bar(top, x="job_count", y="skill", color="skill_category", orientation="h", text="job_count", color_discrete_map=skill_cmap(cats), template=PLOT_TEMPLATE)
                    fig.update_traces(textposition="outside", cliponaxis=False, hovertemplate="%{x}<extra></extra>")
                    return layout(fig, "Top 11 Skills by Job Demand", xtitle="Number of Job Postings", ytitle="Skill")

            with ui.card(class_="module-card", full_screen=True):
                @render_plotly
                def role_category_breakdown():
                    df = unique_jobs()
                    if df.empty:
                        return empty_fig("No jobs for these filters.")
                    g = df.groupby("role_category", as_index=False).size().rename(columns={"size": "count"}).sort_values("count", ascending=False)
                    fig = px.bar(g, x="role_category", y="count", color="role_category", color_discrete_map=role_cmap(g["role_category"].tolist()), template=PLOT_TEMPLATE)
                    fig.update_layout(showlegend=False)
                    fig.update_traces(hovertemplate="%{y:,.0f}<extra></extra>")
                    return layout(fig, "Job Postings by Role Category", xtitle="Role Category", ytitle="Number of Postings", legend=False)

            with ui.card(class_="module-card", full_screen=True):
                @render_plotly
                def title_distribution_chart():
                    df = unique_jobs()
                    tt = df[(df["standardized_title"].notna()) & (df["standardized_title"] != "Unknown")]
                    if tt.empty:
                        return empty_fig("No title data for these filters.")

                    vc = tt.groupby("standardized_title")["job_id"].nunique().sort_values(ascending=False).head(14)
                    plot_df = vc.reset_index(name="count").sort_values("count", ascending=True)

                    fig = px.bar(
                        plot_df,
                        x="count",
                        y="standardized_title",
                        orientation="h",
                        text="count",
                        template=PLOT_TEMPLATE,
                    )

                    fig.update_traces(
                        marker_color="#3b82f6",
                        textposition="outside",
                        cliponaxis=False,
                        hovertemplate="%{x}<extra></extra>"
                    )

                    return layout(fig, "Standardized Job Titles", xtitle="Unique Job Postings", ytitle="Title")