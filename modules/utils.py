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
