# Global AI Job Market Dashboard

An interactive Python Shiny dashboard for exploring global AI job-market patterns from 2020 through 2026. The dashboard combines job-posting data with country-level trend data to make salary, remote-work, role, experience, skill, and job-title patterns easy to compare.

## Features

- **Shared filters** for country, role category, experience level, year range, and maximum salary range.
- **Home dashboard** with live KPIs for unique postings, average maximum salary, remote-job share, and number of countries.
- **Salary Analytics** with:
  - Salary distributions by role category
  - Experience-versus-salary scatter plots for Analytics and Engineering roles
  - Mean maximum salary by role
- **Country Trend** views with country-faceted salary trends over time.
- **Skills & Roles** views with:
  - Top skills by job-posting demand
  - Job postings by role category
  - Standardized job-title distributions
- Interactive Plotly charts with hover details, selectable filters, and full-screen chart support.
- Empty-state messages when a filter combination has insufficient or unavailable data.
- Local CSV-backed data loading, so the app can run without an external database.

## Tech Stack

- **Python 3**
- **Shiny for Python** for the reactive web application and layout
- **shinywidgets** for Plotly integration
- **Pandas** for CSV loading, cleaning, filtering, grouping, and aggregation
- **NumPy** for numerical calculations and salary trend lines
- **Plotly Express and Graph Objects** for interactive visualizations

## Project Structure

```text
.
├── app.py                              # Shiny application and visualization logic
├── requirements.txt                    # Python dependencies and pinned versions
├── data/
│   ├── ai_jobs.csv                     # Base job-posting data
│   ├── master_jobs.csv                 # Enriched job data used by the app
│   ├── country_ai_trends.csv           # Country-year salary and remote-work trends
│   ├── skills_demand.csv               # Job-to-skill mappings
│   ├── job_title_mapping.csv           # Original-to-standardized title mappings
│   └── data_dictionary.csv             # Data-column descriptions
```

The running application currently reads `data/master_jobs.csv` and `data/country_ai_trends.csv`. The other CSV files document or support the data-preparation workflow and are retained as project inputs.

## Requirements

- Python 3.10 or newer is recommended.
- A terminal with access to this project directory.
- The CSV files in `data/` must remain available relative to `app.py`.

## Installation

1. Clone or download the repository and move into the project directory:

   ```bash
   cd ai-job-market-dashboard
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   On Windows PowerShell, use:

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

3. Install the pinned dependencies:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

## Run Locally

From the project root, with the virtual environment active, start the Shiny development server:

```bash
shiny run --reload app.py
```

Open the local URL printed in the terminal, typically `http://127.0.0.1:8000`.

To make the app available to other devices on the same network, bind the server to all interfaces:

```bash
shiny run --reload --host 0.0.0.0 app.py
```

## Using the Dashboard

1. Open the **Home** tab to review the high-level KPIs and country comparisons.
2. Use the sidebar filters to select countries, role categories, experience levels, years, and salary limits.
3. Move to **Salary Analytics** to compare salary distributions and the relationship between experience and salary.
4. Use **Country Trend** to inspect salary trajectories for each selected country in separate panels.
5. Use **Skills & Roles** to rank skills, compare role categories, and inspect standardized job titles.
6. Hover over chart marks for exact values. Charts can be expanded using the Plotly full-screen control.

The dashboard applies the selected country, role, experience, year, and salary filters reactively. Country trend charts use the selected year range and countries; job-level charts additionally use role, experience, and salary filters where applicable.

## Data Notes

### Runtime datasets

- `master_jobs.csv` contains the enriched job-level records used for job counts, salary analysis, role analysis, title analysis, and skill analysis. It includes fields such as `job_id`, `country`, `role_category`, `experience_level`, `salary_min_usd`, `salary_max_usd`, `posted_year`, `standardized_title`, `skill`, and `skill_category`.
- `country_ai_trends.csv` contains country-year aggregates used for salary and remote-work trend charts. Important fields include `country`, `year`, `avg_salary_usd`, `remote_percentage`, and `total_ai_jobs`.

The app normalizes missing categorical values to `Unknown`, converts numeric fields before filtering, limits displayed years to 2020-2026, and deduplicates job IDs for unique-posting KPIs and most job-level summaries. Skill demand counts are based on unique job IDs.

### Supporting datasets

- `ai_jobs.csv` contains the base job-posting fields, including company, industry, location, work arrangement, experience, salary, employment type, and posting year.
- `skills_demand.csv` maps jobs to required skills, skill categories, and skill levels.
- `job_title_mapping.csv` maps original job titles to standardized titles and role categories.
- `data_dictionary.csv` records definitions for selected columns.

If the CSV schema changes, update the corresponding loading and transformation logic in `app.py` as well as this documentation.

## Development Notes

- Keep data paths relative to `app.py`; the application resolves them from its own directory so local and deployed execution use the same layout.
- Preserve the columns required by `load_jobs()` and `load_trends()` when replacing data files.
- Install updated dependencies in a virtual environment and update `requirements.txt` when the runtime stack changes.
- The app is designed around reactive calculations, so chart outputs should consume the existing filtered data calculations when adding new views.

## License and Data Provenance

No license or external data-provenance statement is currently included in this repository. Add the appropriate licensing and source information before public redistribution or production deployment.