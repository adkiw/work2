import streamlit as st


def rerun() -> None:
    """Rerun the Streamlit app in a version-compatible way."""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        # Fallback for older Streamlit versions
        st.experimental_rerun()


def title_with_add(title: str, button_label: str, on_click=None):
    """Display a page title with an aligned "add" button."""
    left, right = st.columns([9, 1])
    left.title(title)
    return right.button(button_label, on_click=on_click, use_container_width=True)

def display_table_with_edit(df, edit_callback=None, id_col="id"):
    """Display a dataframe with a column of edit buttons.

    Parameters
    ----------
    df : pandas.DataFrame
        Data to display.
    edit_callback : callable or None
        Function to call with the row identifier when an edit button is clicked.
        If None, the dataframe is displayed without edit buttons.
    id_col : str
        Name of the column containing the unique row identifier.
    """
    if df is None or df.empty:
        st.dataframe(df)
        return

    if id_col not in df.columns:
        id_col = df.columns[0]

    df_disp = df.reset_index(drop=True).copy()

    if edit_callback is None:
        st.dataframe(df_disp, hide_index=True)
        return

    try:
        df_disp["✏️"] = ""

        def _on_click(row):
            rid = df_disp.loc[row, id_col]
            edit_callback(rid)

        st.data_editor(
            df_disp,
            hide_index=True,
            disabled=True,
            column_config={
                "✏️": st.column_config.ButtonColumn(
                    label="✏️",
                    on_click=_on_click,
                )
            },
            use_container_width=True,
        )
    except Exception:
        for _, row in df_disp.iterrows():
            cols = st.columns(len(df_disp.columns) + 1)
            for i, col in enumerate(df_disp.columns[:-1]):
                cols[i].write(row[col])
            cols[-1].button(
                "✏️",
                key=f"edit_{row[id_col]}",
                on_click=edit_callback,
                args=(row[id_col],),
            )

