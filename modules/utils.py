import streamlit as st


def rerun() -> None:
    """Rerun the Streamlit app in a version-compatible way."""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        # Fallback for older Streamlit versions
        st.experimental_rerun()


def title_with_add(title: str, button_label: str, on_click=None, *, key: str | None = None):
    """Display a page title with an aligned "add" button.

    Parameters
    ----------
    title:
        The title text to display.
    button_label:
        The label for the action button.
    on_click:
        Optional callback to run when the button is clicked.
    key:
        Optional Streamlit widget key to allow multiple instances on the same page.
    """

    left, right = st.columns([9, 1])
    left.title(title)
    return right.button(
        button_label,
        on_click=on_click,
        use_container_width=True,
        key=key,
    )
