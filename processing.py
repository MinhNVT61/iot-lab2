import pandas as pd
from sklearn.preprocessing import StandardScaler
def process(frame):
    outputs=[]
    for device,g in frame.groupby("device_id"):
        g=g.sort_values("_time").drop_duplicates("_time").set_index("_time")
        raw=g[["temperature","humidity","distance_cm"]].astype(float)
        # Align to nominal five-second slots; retain one sample per slot.
        grid=raw.resample("5s").mean()
        observed=grid.notna().all(axis=1)
        clean=grid.copy(); flags=pd.DataFrame(False,index=grid.index,columns=grid.columns)
        for k in grid:
            q1,q3=grid[k].quantile([.25,.75]); spread=q3-q1
            flags[k]=((grid[k]<q1-1.5*spread)|(grid[k]>q3+1.5*spread)) if spread>0 else (grid[k].notna() & (grid[k]!=q1))
            clean.loc[flags[k],k]=float("nan")
            # Fill only whole internal gaps of <=2 samples, never partial long gaps.
            missing=clean[k].isna(); groups=missing.ne(missing.shift()).cumsum()
            lengths=missing.groupby(groups).transform("sum")
            candidate=clean[k].interpolate(method="time",limit_area="inside")
            clean.loc[missing & (lengths<=2),k]=candidate
        out=clean.resample("1min").mean()
        out["sample_count"]=observed.resample("1min").sum()
        out["missing_count"]=(~observed).resample("1min").sum()
        out["outlier_count"]=flags.sum(axis=1).resample("1min").sum()
        for k in clean:
            out[k+"_rolling_mean"]=out[k].rolling(5,min_periods=1).mean()
            out[k+"_delta"]=out[k].diff()
            out[k+"_scaled"]=float("nan")
            valid=out[k].notna()
            if valid.any(): out.loc[valid,k+"_scaled"]=StandardScaler().fit_transform(out.loc[valid,[k]]).ravel()
        out["device_id"]=device
        outputs.append(out.reset_index())
    return pd.concat(outputs,ignore_index=True) if outputs else pd.DataFrame()
