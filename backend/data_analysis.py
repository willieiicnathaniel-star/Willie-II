"""
THEeye - Advanced Data Analysis Module
Dataset upload, analysis execution, visualization, online data extraction, model suggestion.
"""
import io, base64, os, tempfile

def parse_dataset(file_bytes, filename):
    import pandas as pd
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "csv"
    if ext in ("xlsx", "xls"):
        df = pd.read_excel(io.BytesIO(file_bytes))
    elif ext == "json":
        df = pd.read_json(io.BytesIO(file_bytes))
    elif ext == "tsv":
        df = pd.read_csv(io.BytesIO(file_bytes), sep="\t")
    else:
        df = pd.read_csv(io.BytesIO(file_bytes))
    summary = {
        "columns": list(df.columns), "n_rows": int(len(df)), "n_cols": int(len(df.columns)),
        "dtypes": {c: str(df[c].dtype) for c in df.columns},
        "head": df.head(10).fillna("N/A").to_dict(orient="records"),
        "describe": {}, "missing_values": {},
    }
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if numeric_cols:
        summary["describe"] = df[numeric_cols].describe().round(4).to_dict()
    for col in df.columns:
        m = int(df[col].isna().sum())
        if m > 0: summary["missing_values"][col] = m
    temp_path = os.path.join(tempfile.gettempdir(), "theeye_current_dataset.csv")
    df.to_csv(temp_path, index=False)
    summary["_temp_path"] = temp_path
    return summary

def execute_analysis(instruction, dataset_path, tool="python"):
    import pandas as pd, numpy as np
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    from scipy import stats as sp
    import statsmodels.api as sm
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({"figure.dpi": 150, "savefig.dpi": 300, "figure.figsize": (10, 6)})
    df = pd.read_csv(dataset_path)
    il = instruction.lower()
    results = {"text_output": "", "plots": [], "tables": [], "code_generated": ""}
    nc = df.select_dtypes(include=["number"]).columns.tolist()
    cc = df.select_dtypes(include=["object", "category"]).columns.tolist()

    if any(k in il for k in ["descriptive", "summary", "describe", "overview"]):
        if nc:
            results["tables"].append({"title": "Descriptive Statistics", "data": df[nc].describe().round(4).to_dict()})
            results["text_output"] += f"\nDescriptive Statistics: {len(df)} rows, {len(df.columns)} columns\n"
            fig, ax = plt.subplots(figsize=(12, 6))
            df[nc[:8]].boxplot(ax=ax, patch_artist=True)
            ax.set_title("Box Plot", fontsize=14, fontweight="bold")
            plt.xticks(rotation=45, ha="right"); plt.tight_layout()
            results["plots"].append({"title": "Box Plot", "image": _fig_b64(fig), "format": "png"})
            plt.close(fig)

    if any(k in il for k in ["correlation", "correlate", "relationship"]):
        if len(nc) >= 2:
            corr = df[nc].corr().round(4)
            results["tables"].append({"title": "Correlation Matrix", "data": corr.to_dict()})
            fig, ax = plt.subplots(figsize=(10, 8))
            sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, square=True, linewidths=0.5, ax=ax)
            ax.set_title("Correlation Heatmap", fontsize=14, fontweight="bold"); plt.tight_layout()
            results["plots"].append({"title": "Correlation Heatmap", "image": _fig_b64(fig), "format": "png"})
            plt.close(fig)

    if any(k in il for k in ["regression", "ols", "regress"]):
        if len(nc) >= 2:
            dep = nc[0]; ind = nc[1:6]
            for c in nc:
                if c.lower() in il: dep = c; ind = [x for x in nc if x != dep][:5]; break
            X = df[ind].dropna(); y = df.loc[X.index, dep]
            X = sm.add_constant(X); model = sm.OLS(y, X).fit()
            results["text_output"] += f"\nOLS: dep={dep}, R2={model.rsquared:.4f}, adj_R2={model.rsquared_adj:.4f}\n"
            results["text_output"] += model.summary().as_text() + "\n"
            fig, ax = plt.subplots(figsize=(10, 6))
            coefs = model.params[1:]; errs = model.bse[1:]
            colors = ["#2ecc71" if c > 0 else "#e74c3c" for c in coefs]
            ax.barh(range(len(coefs)), coefs, xerr=errs, color=colors, alpha=0.8, capsize=5)
            ax.set_yticks(range(len(coefs))); ax.set_yticklabels(coefs.index)
            ax.axvline(0, color="black", linewidth=0.8, linestyle="--")
            ax.set_title("Regression Coefficients", fontsize=14, fontweight="bold"); plt.tight_layout()
            results["plots"].append({"title": "Coefficients", "image": _fig_b64(fig), "format": "png"})
            plt.close(fig)
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.scatter(model.fittedvalues, model.resid, alpha=0.6, edgecolors="black", linewidth=0.5)
            ax.axhline(0, color="red", linewidth=1, linestyle="--")
            ax.set_xlabel("Fitted"); ax.set_ylabel("Residuals")
            ax.set_title("Residual Plot", fontsize=14, fontweight="bold"); plt.tight_layout()
            results["plots"].append({"title": "Residuals", "image": _fig_b64(fig), "format": "png"})
            plt.close(fig)

    if any(k in il for k in ["histogram", "distribution", "density", "normality"]):
        for col in nc[:4]:
            fig, axes = plt.subplots(1, 2, figsize=(14, 5))
            axes[0].hist(df[col].dropna(), bins=30, color="steelblue", edgecolor="white", alpha=0.8)
            axes[0].set_title(f"Histogram - {col}", fontweight="bold")
            from scipy.stats import probplot
            probplot(df[col].dropna(), dist="norm", plot=axes[1])
            axes[1].set_title(f"Q-Q Plot - {col}", fontweight="bold")
            plt.tight_layout()
            results["plots"].append({"title": f"Distribution - {col}", "image": _fig_b64(fig), "format": "png"})
            plt.close(fig)
            stat, p = sp.shapiro(df[col].dropna()[:5000])
            results["text_output"] += f"\nShapiro-Wilk {col}: W={stat:.4f}, p={p:.6f} {'(Normal)' if p > 0.05 else '(Non-normal)'}\n"

    if any(k in il for k in ["scatter", "plot", "visualize"]):
        if len(nc) >= 2:
            x, y = nc[0], nc[1]
            fig, ax = plt.subplots(figsize=(10, 7))
            ax.scatter(df[x], df[y], alpha=0.6, edgecolors="black", linewidth=0.5, s=50)
            mask = df[[x, y]].dropna()
            if len(mask) > 2:
                z = np.polyfit(mask[x], mask[y], 1); p = np.poly1d(z)
                ax.plot(mask[x], p(mask[x]), "r--", linewidth=2, label=f"y={z[0]:.4f}x+{z[1]:.4f}")
                ax.legend()
            ax.set_xlabel(x); ax.set_ylabel(y)
            ax.set_title(f"Scatter: {y} vs {x}", fontsize=14, fontweight="bold"); plt.tight_layout()
            results["plots"].append({"title": f"Scatter: {y} vs {x}", "image": _fig_b64(fig), "format": "png"})
            plt.close(fig)

    if any(k in il for k in ["time series", "trend", "forecast", "arima"]):
        if nc:
            col = nc[0]
            for c in nc:
                if c.lower() in il: col = c; break
            fig, axes = plt.subplots(2, 1, figsize=(14, 10))
            axes[0].plot(df[col], color="steelblue", linewidth=1.5)
            axes[0].set_title(f"Time Series - {col}", fontsize=14, fontweight="bold")
            rolling = df[col].rolling(window=12).mean()
            axes[1].plot(df[col], color="lightgray", linewidth=1, label="Original")
            axes[1].plot(rolling, color="red", linewidth=2, label="Rolling Mean")
            axes[1].legend(); plt.tight_layout()
            results["plots"].append({"title": f"Time Series - {col}", "image": _fig_b64(fig), "format": "png"})
            plt.close(fig)

    if any(k in il for k in ["bar chart", "bar plot", "bar graph"]):
        if cc:
            col = cc[0]
            for c in cc:
                if c.lower() in il: col = c; break
            counts = df[col].value_counts().head(15)
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.bar(range(len(counts)), counts.values, color="steelblue", edgecolor="white")
            ax.set_xticks(range(len(counts))); ax.set_xticklabels(counts.index, rotation=45, ha="right")
            ax.set_title(f"Bar Chart - {col}", fontsize=14, fontweight="bold"); plt.tight_layout()
            results["plots"].append({"title": f"Bar - {col}", "image": _fig_b64(fig), "format": "png"})
            plt.close(fig)

    results["code_generated"] = _gen_code(tool, instruction, nc, cc)
    if not results["plots"] and not results["text_output"]:
        results["text_output"] = "Try: descriptive statistics, correlation, OLS regression, histogram, scatter plot, time series, or bar chart."
    return results

def _gen_code(tool, instruction, nc, cc):
    dep = nc[0] if nc else "y"
    ind = nc[1:5] if len(nc) > 1 else ["x1", "x2"]
    s = " + ".join(ind)
    if tool in ("r", "rstudio"):
        return f"# R Code\nlibrary(tidyverse); library(stargazer)\ndata <- read.csv('dataset.csv')\nsummary(data)\nmodel <- lm({dep} ~ {s}, data=data)\nsummary(model)\nstargazer(model, type='text')"
    elif tool == "stata":
        return f"* Stata 18\nuse 'dataset.dta', clear\nsummarize {dep} {' '.join(ind)}\nregress {dep} {' '.join(ind)}, robust\npwcorr {dep} {' '.join(ind)}, sig"
    elif tool == "eviews":
        return f"' EViews\nimport 'dataset.csv'\nequation eq1.ls {dep} c {' '.join(ind)}\nshow eq1"
    return f"# Python\nimport pandas as pd, statsmodels.api as sm\ndf = pd.read_csv('dataset.csv')\nX = sm.add_constant(df[{ind}]); y = df['{dep}']\nmodel = sm.OLS(y, X).fit()\nprint(model.summary())"

def extract_online_data(source, query, params=None):
    params = params or {}
    sl = source.lower()
    if "world" in sl: return _wb(query, params)
    if "imf" in sl: return _imf(query, params)
    if "oecd" in sl: return _oecd(query, params)
    if "fred" in sl: return {"error": "FRED requires API key."}
    return {"error": f"Unknown source: {source}"}

def _wb(query, params):
    import httpx, pandas as pd
    country = params.get("country", "all")
    dr = params.get("date_range", "2000:2024")
    url = f"https://api.worldbank.org/v2/country/{country}/indicator/{query}?date={dr}&format=json&per_page=10000"
    try:
        r = httpx.get(url, timeout=30); d = r.json()
        if len(d) < 2 or not d[1]: return {"error": "No data found."}
        recs = d[1]; df = pd.DataFrame(recs)
        cols = ["country", "countryiso3code", "date", "value", "indicator"]
        av = [c for c in cols if c in df.columns]
        return {"source": "World Bank", "indicator": query, "n_records": len(recs),
                "columns": list(df.columns), "head": df[av].head(20).fillna("N/A").to_dict(orient="records"),
                "download_url": url, "message": f"Retrieved {len(recs)} records."}
    except Exception as e:
        return {"error": str(e)}

def _imf(query, params):
    import httpx
    try:
        r = httpx.get(f"https://www.imf.org/external/datamapper/api/v1/{query}", timeout=30)
        return {"source": "IMF", "data": r.json().get("values", {}), "message": f"Retrieved IMF data for {query}"}
    except Exception as e:
        return {"error": str(e)}

def _oecd(query, params):
    import httpx
    try:
        r = httpx.get(f"https://stats.oecd.org/SDMX-JSON/data/{query}/all?startTime=2000&endTime=2024", timeout=30)
        return {"source": "OECD", "message": f"Retrieved OECD data for {query}", "raw": r.text[:2000]}
    except Exception as e:
        return {"error": str(e)}

def suggest_econometric_model(methodology):
    t = methodology.lower()
    suggestions = []
    if any(k in t for k in ["panel", "cross-country", "longitudinal", "fixed effect", "random effect", "firm-level"]):
        suggestions.append({"model": "Panel Data (FE/RE)", "description": "For cross-country/firm data over time.", "methods": ["Fixed Effects", "Random Effects", "Hausman Test"], "software": "R: plm() | Stata: xtreg | Python: linearmodels", "assumptions": ["Entity heterogeneity", "Strict exogeneity"], "score": 95})
    if any(k in t for k in ["time series", "temporal", "forecast", "trend", "arima", "var", "granger"]):
        suggestions.append({"model": "Time Series (ARIMA/VAR)", "description": "For temporal data and forecasting.", "methods": ["ARIMA", "VAR", "Granger Causality"], "software": "R: auto.arima() | Stata: arima | Python: statsmodels.tsa", "assumptions": ["Stationarity", "No autocorrelation"], "score": 90})
    if any(k in t for k in ["endogeneity", "endogenous", "instrument", "iv", "2sls", "gmm", "causal"]):
        suggestions.append({"model": "IV/2SLS/GMM", "description": "Addresses endogeneity bias.", "methods": ["2SLS", "GMM", "Weak Instrument Test"], "software": "R: ivreg() | Stata: ivregress | Python: linearmodels.IV2SLS", "assumptions": ["Instrument relevance", "Exclusion restriction"], "score": 88})
    if any(k in t for k in ["did", "difference-in-differences", "treatment", "policy evaluation", "natural experiment"]):
        suggestions.append({"model": "Difference-in-Differences", "description": "For policy intervention effects.", "methods": ["Two-way DiD", "Event Study", "Parallel Trends"], "software": "R: feols() | Stata: csdid | Python: differences", "assumptions": ["Parallel trends", "No anticipation"], "score": 92})
    if any(k in t for k in ["binary", "dummy", "logit", "probit", "choice", "0/1", "probability"]):
        suggestions.append({"model": "Logit/Probit", "description": "For binary outcomes.", "methods": ["Logistic", "Probit", "Marginal Effects"], "software": "R: glm() | Stata: logit | Python: sklearn", "assumptions": ["Independence", "No multicollinearity"], "score": 85})
    if any(k in t for k in ["ols", "regression", "cross-section", "linear"]):
        suggestions.append({"model": "OLS Regression", "description": "Standard linear regression baseline.", "methods": ["OLS with Robust SE", "VIF", "Breusch-Pagan"], "software": "R: lm() | Stata: regress | Python: statsmodels.OLS", "assumptions": ["Linearity", "Homoscedasticity", "Normality"], "score": 75})
    if any(k in t for k in ["spatial", "geography", "neighbor", "distance"]):
        suggestions.append({"model": "Spatial Econometrics", "description": "For spatial dependencies.", "methods": ["SAR", "SEM", "SDM"], "software": "R: spdep | Stata: spreg | Python: pysal", "assumptions": ["Spatial autocorrelation"], "score": 82})
    if any(k in t for k in ["dynamic panel", "gmm", "arellano", "blundell", "lagged"]):
        suggestions.append({"model": "Dynamic Panel GMM", "description": "Dynamic panel with lagged DV.", "methods": ["Difference GMM", "System GMM", "Sargan Test"], "software": "R: pgmm() | Stata: xtabond2 | Python: linearmodels", "assumptions": ["No AR(2)", "Valid instruments"], "score": 91})
    if not suggestions:
        suggestions.append({"model": "OLS (Baseline)", "description": "Start with OLS baseline.", "methods": ["OLS", "Diagnostics"], "software": "R: lm() | Stata: regress", "assumptions": ["Linearity", "Independence"], "score": 60})
    suggestions.sort(key=lambda x: x["score"], reverse=True)
    return {"primary_recommendation": suggestions[0], "all_suggestions": suggestions,
            "note": "Verify assumptions and test specifications before finalizing."}

def generate_tool_code(tool, method, independent_vars, control_vars=None):
    """Generate analysis code for a given tool and method.
    Called from main.py /api/analysis/generate-code endpoint.
    """
    control_vars = control_vars or []
    dep = independent_vars[0] if independent_vars else "y"
    indep = independent_vars[1:] if len(independent_vars) > 1 else (independent_vars if independent_vars else ["x1"])
    all_vars = indep + control_vars
    indep_str = " + ".join(all_vars) if all_vars else "x"
    tool = (tool or "python").lower()

    if tool in ("r", "rstudio"):
        return _gen_r_code(method, dep, indep, control_vars, all_vars, indep_str)
    elif tool == "stata":
        return _gen_stata_code(method, dep, indep, control_vars, all_vars, indep_str)
    elif tool == "eviews":
        return _gen_eviews_code(method, dep, indep, all_vars, indep_str)
    return _gen_python_code(method, dep, indep, control_vars, all_vars, indep_str)


def _gen_python_code(method, dep, indep, controls, all_vars, indep_str):
    import_str = "import pandas as pd\nimport numpy as np\nimport statsmodels.api as sm\nimport matplotlib.pyplot as plt\nimport seaborn as sns\n\n"
    load = "df = pd.read_csv('dataset.csv')\n\n"
    if method == "descriptive":
        return import_str + load + "print(df.describe())\ndf.hist(figsize=(12,8), bins=30)\nplt.tight_layout()\nplt.savefig('descriptive.png', dpi=300)\n"
    if method == "correlation":
        return import_str + load + "corr = df.corr()\nprint(corr)\nsns.heatmap(corr, annot=True, cmap='coolwarm', center=0)\nplt.title('Correlation Matrix')\nplt.tight_layout()\nplt.savefig('correlation.png', dpi=300)\n"
    if method == "ols":
        return import_str + load + f"X = sm.add_constant(df[{all_vars!r}])\ny = df['{dep}']\nmodel = sm.OLS(y, X).fit()\nprint(model.summary())\n"
    if method in ("panel_fixed", "panel"):
        return import_str + "from linearmodels import PanelOLS\n" + load + f"df = df.set_index(['entity', 'time'])\nmodel = PanelOLS(df['{dep}'], sm.add_constant(df[{all_vars!r}]), entity_effects=True)\nresult = model.fit()\nprint(result.summary())\n"
    if method == "logistic":
        return import_str + load + f"X = sm.add_constant(df[{all_vars!r}])\ny = df['{dep}']\nmodel = sm.Logit(y, X).fit()\nprint(model.summary())\nprint('Odds Ratios:', np.exp(model.params))\n"
    if method in ("iv_2sls", "iv"):
        return import_str + "from linearmodels import IV2SLS\n" + load + f"model = IV2SLS(df['{dep}'], sm.add_constant(df[{controls!r}]), df[{indep!r}], df[['z1']]).fit()\nprint(model.summary())\n"
    if method == "did":
        return import_str + load + f"df['treated_post'] = df['treated'] * df['post']\nX = sm.add_constant(df[['treated','post','treated_post']])\nmodel = sm.OLS(df['{dep}'], X).fit()\nprint(model.summary())\n"
    if method == "time_series":
        return import_str + "from statsmodels.tsa.arima.model import ARIMA\n" + load + f"model = ARIMA(df['{dep}'], order=(1,1,1)).fit()\nprint(model.summary())\nforecast = model.forecast(steps=12)\nprint('Forecast:', forecast)\n"
    return import_str + load + f"X = sm.add_constant(df[{all_vars!r}])\ny = df['{dep}']\nmodel = sm.OLS(y, X).fit()\nprint(model.summary())\n"


def _gen_r_code(method, dep, indep, controls, all_vars, indep_str):
    header = "library(tidyverse)\nlibrary(stargazer)\nlibrary(sandwich)\nlibrary(lmtest)\n\n"
    load = "data <- read.csv('dataset.csv')\n\n"
    if method == "descriptive":
        return header + load + "summary(data)\ncor(data)\n"
    if method == "correlation":
        return header + "library(corrplot)\n" + load + "corr <- cor(data, use='complete.obs')\nprint(corr)\ncorrplot(corr, method='color', type='upper')\n"
    if method == "ols":
        return header + load + f"model <- lm({dep} ~ {indep_str}, data=data)\nsummary(model)\ncoeftest(model, vcov=vcovHC(model, type='HC1'))\nstargazer(model, type='text')\n"
    if method in ("panel_fixed", "panel"):
        return header + "library(plm)\n" + load + f"pdata <- pdata.frame(data, index=c('entity','time'))\nfe <- plm({dep} ~ {indep_str}, data=pdata, model='within')\nre <- plm({dep} ~ {indep_str}, data=pdata, model='random')\nsummary(fe)\nphtest(fe, re)\n"
    if method == "logistic":
        return header + load + f"logit <- glm({dep} ~ {indep_str}, data=data, family=binomial)\nsummary(logit)\nexp(coef(logit))\n"
    if method in ("iv_2sls", "iv"):
        return header + "library(AER)\n" + load + f"iv <- ivreg({dep} ~ {indep_str} | z1, data=data)\nsummary(iv, diagnostics=TRUE)\n"
    if method == "did":
        return header + "library(fixest)\n" + load + f"did <- feols({dep} ~ treated:post | entity + time, data=data)\nsummary(did)\n"
    if method == "time_series":
        return header + "library(forecast)\n" + load + f"ts_data <- ts(data${dep}, frequency=12)\nmodel <- auto.arima(ts_data)\nsummary(model)\nforecast(model, h=12)\n"
    return header + load + f"model <- lm({dep} ~ {indep_str}, data=data)\nsummary(model)\n"


def _gen_stata_code(method, dep, indep, controls, all_vars, indep_str):
    load = "use 'dataset.dta', clear\n\n"
    if method == "descriptive":
        return "* Stata 18\n" + load + "summarize\n"
    if method == "correlation":
        return "* Stata 18\n" + load + f"pwcorr {dep} {' '.join(all_vars)}, sig\n"
    if method == "ols":
        return "* Stata 18\n" + load + f"regress {dep} {' '.join(all_vars)}, robust\nestat vif\nrvfplot\n"
    if method in ("panel_fixed", "panel"):
        return "* Stata 18\n" + load + f"xtset entity time\nxtreg {dep} {' '.join(all_vars)}, fe\nxtreg {dep} {' '.join(all_vars)}, re\nhausman fe re\n"
    if method == "logistic":
        return "* Stata 18\n" + load + f"logit {dep} {' '.join(all_vars)}, robust\nmargins, dydx(*)\n"
    if method in ("iv_2sls", "iv"):
        return "* Stata 18\n" + load + f"ivregress 2sls {dep} ({indep[0] if indep else 'x'} = z1) {' '.join(controls)}, robust\nestat endogenous\nestat firststage\n"
    if method == "did":
        return "* Stata 18\n" + load + f"gen treated_post = treated * post\nregress {dep} treated post treated_post, robust\n"
    if method == "time_series":
        return "* Stata 18\n" + load + f"tsset time\narima {dep}, arima(1,1,1)\nforecast\n"
    return "* Stata 18\n" + load + f"regress {dep} {' '.join(all_vars)}, robust\n"


def _gen_eviews_code(method, dep, indep, all_vars, indep_str):
    load = "import 'dataset.csv'\n\n"
    if method == "ols":
        return "' EViews\n" + load + f"equation eq1.ls {dep} c {' '.join(all_vars)}\nshow eq1\n"
    if method == "logistic":
        return "' EViews\n" + load + f"binary b1.ls {dep} c {' '.join(all_vars)}\nshow b1\n"
    if method == "time_series":
        return "' EViews\n" + load + f"equation ts1.ls {dep} ar(1) ma(1)\nshow ts1\n"
    return "' EViews\n" + load + f"equation eq1.ls {dep} c {' '.join(all_vars)}\nshow eq1\n"


def _fig_b64(fig, fmt="png"):
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, dpi=300, bbox_inches="tight", facecolor="white")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")