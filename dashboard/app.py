"""
Streamlit Dashboard MVP for the Discovery Engine.

Interactive UI for product researchers to query the RAG engine
and explore the corpus of user feedback.

Usage:
    streamlit run dashboard/app.py
"""

import sys
import os
import streamlit as st

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rag.engine import RAGEngine
from storage.metadata_repo import MetadataRepository
from storage.models import get_engine

# --- Configuration & Initialization ---
st.set_page_config(
    page_title="Discovery Engine",
    page_icon="🔍",
    layout="wide",
)

def check_password():
    """Returns `True` if the user had a correct password."""

    def password_entered():
        if st.session_state["password"] == "admin":  # Default simple password
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        return True

if not check_password():
    st.stop()


@st.cache_resource
def get_db_repo():
    engine = get_engine()
    return MetadataRepository(engine)

@st.cache_resource
def get_rag_engine():
    return RAGEngine()

repo = get_db_repo()
rag = get_rag_engine()

# --- UI Components ---
st.title("🔍 Photo Retrieval Discovery Engine")
st.markdown("Query public user feedback to uncover how people search for and fail to retrieve photos.")

# Sidebar Navigation
page = st.sidebar.radio(
    "Navigation",
    ["Discovery Queries", "Cross-Platform Comparison", "Corpus Analytics", "Source Explorer"]
)

if page == "Discovery Queries":
    st.header("Discovery Queries")
    
    # Pre-defined discovery questions
    st.subheader("Standard Research Questions")
    
    discovery_questions = {
        "Custom Query": None,
        "What kinds of old photos do users struggle to retrieve?": "photo_types",
        "What information do people actually remember about a photo?": "what_users_remember",
        "What information have users forgotten?": "what_users_forget",
        "How do users formulate searches?": "search_strategies",
        "What are the cascading failure loops?": "failure_cascades"
    }
    
    selected_q = st.selectbox("Select a question:", list(discovery_questions.keys()))
    
    if selected_q == "Custom Query":
        custom_q = st.text_input("Enter your custom research question:")
    else:
        custom_q = selected_q
        
    namespace_filter = st.multiselect(
        "Filter by Platform",
        ["google_play", "apple_app_store", "reddit_threads", "support_forums", "youtube_comments"],
        default=["google_play", "apple_app_store", "reddit_threads", "support_forums", "youtube_comments"]
    )
        
    if st.button("Generate Insights", type="primary") and custom_q:
        with st.spinner("Retrieving feedback & synthesizing insights (this may take a minute)..."):
            try:
                discovery_key = discovery_questions.get(selected_q)
                results = rag.query(
                    question=custom_q,
                    namespaces=namespace_filter,
                    top_k=20,
                    discovery_key=discovery_key
                )
                
                st.markdown("### 💡 Insights")
                st.markdown(results["answer"])
                
                with st.expander("View Source Evidence (Retrieved Chunks)"):
                    for i, chunk in enumerate(results["retrieved_chunks"], 1):
                        meta = chunk.get("metadata", {})
                        st.markdown(f"**[{meta.get('source_platform', 'unknown')}]** {meta.get('app_referenced', '')}")
                        st.info(meta.get("text", chunk.get("text", "")))
                        st.caption(f"Relevance Score: {chunk.get('score', 0):.4f}")
                        st.divider()
                        
            except Exception as e:
                st.error(f"Failed to run query: {str(e)}")

elif page == "Cross-Platform Comparison":
    st.header("Cross-Platform Comparison Engine")
    st.markdown("Run a discovery query across multiple platforms independently and synthesize their differences.")
    
    from rag.comparator import CrossPlatformComparator
    
    @st.cache_resource
    def get_comparator():
        return CrossPlatformComparator(rag_engine=get_rag_engine())
        
    comparator = get_comparator()
    
    compare_q = st.text_input("Enter a research question to compare across platforms:", "What metadata do users forget most?")
    
    compare_namespaces = st.multiselect(
        "Select Platforms to Compare",
        ["google_play", "apple_app_store", "reddit_threads", "support_forums", "youtube_comments"],
        default=["google_play", "apple_app_store", "reddit_threads"]
    )
    
    if st.button("Compare Platforms", type="primary") and compare_q:
        if len(compare_namespaces) < 2:
            st.warning("Please select at least 2 platforms to compare.")
        else:
            with st.spinner("Querying platforms and synthesizing comparison..."):
                try:
                    result = comparator.compare(question=compare_q, namespaces=compare_namespaces)
                    comp = result.get("comparison", {})
                    
                    if "error" in comp:
                        st.error(f"Comparison Synthesis Error: {comp['error']}")
                    else:
                        st.markdown("### 📊 Synthesis Summary")
                        st.info(comp.get("synthesis_summary", ""))
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("### 🤝 Similarities")
                            for sim in comp.get("similarities", []):
                                st.markdown(f"- {sim}")
                                
                        with col2:
                            st.markdown("### ⚡ Differences")
                            for diff in comp.get("differences", []):
                                st.markdown(f"- {diff}")
                                
                        st.markdown("### 🔍 Platform Quirks")
                        for platform, quirk in comp.get("platform_quirks", {}).items():
                            st.markdown(f"- **{platform.title()}**: {quirk}")
                            
                        st.divider()
                        st.markdown("### 📝 Detailed Platform Answers")
                        for platform, answer in result.get("platform_answers", {}).items():
                            with st.expander(f"{platform.title()} Answer"):
                                st.markdown(answer)
                                
                except Exception as e:
                    st.error(f"Failed to run comparison: {str(e)}")

elif page == "Corpus Analytics":
    st.header("Corpus Analytics")
    
    try:
        stats = repo.get_stats()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Chunks Ingested", stats["total_chunks"])
        
        st.subheader("Data by Platform")
        st.bar_chart(stats["by_platform"])
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Taxonomy Distribution")
            st.bar_chart(stats["by_taxonomy"])
            
        with col2:
            st.subheader("Frustration Levels")
            st.bar_chart(stats["by_frustration"])
            
    except Exception as e:
        st.error("Database connection failed. Are migrations applied and Postgres running?")
        st.code(str(e))

elif page == "Source Explorer":
    st.header("Source Explorer")
    st.markdown("Browse raw feedback by platform.")
    
    platform = st.selectbox(
        "Platform", 
        ["google_play", "apple_app_store", "reddit_threads", "support_forums", "youtube_comments"]
    )
    
    try:
        chunks = repo.get_chunks_by_platform(platform, limit=50)
        st.write(f"Showing latest 50 chunks for **{platform}**")
        
        for c in chunks:
            with st.container(border=True):
                st.markdown(f"**App:** {c.app_referenced or 'N/A'} | **Taxonomy:** {c.taxonomy_label or 'N/A'}")
                st.write(c.original_text)
                if c.source_url:
                    st.caption(f"[Source Link]({c.source_url})")
    except Exception as e:
        st.error("Could not fetch data.")
        st.code(str(e))
