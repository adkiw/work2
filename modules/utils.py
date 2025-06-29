import streamlit as st


def rerun() -> None:
    """Rerun the Streamlit app in a version-compatible way."""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        # Fallback for older Streamlit versions
        st.experimental_rerun()
