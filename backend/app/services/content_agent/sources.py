"""
Content agent source registry.
ALL sources here are 100% free — no paid APIs required for data collection.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

SourceType = Literal["rss", "nitter", "youtube", "github", "reddit", "hackernews", "linkedin_scrape"]


@dataclass
class Source:
    key: str
    label: str
    type: SourceType
    url: str
    priority: int = 5
    tags: list[str] = field(default_factory=list)


# Nitter instances — public X/Twitter mirrors with RSS, no API key needed
NITTER_INSTANCES = [
    "nitter.poast.org",
    "nitter.privacydev.net",
    "xcancel.com",
]

NITTER_ACCOUNTS = [
    ("openai",         "OpenAI",              1, ["ai", "model_release"]),
    ("sama",           "Sam Altman",          1, ["ai", "opinion"]),
    ("AnthropicAI",    "Anthropic",           1, ["ai", "safety"]),
    ("GoogleDeepMind", "Google DeepMind",     1, ["ai", "research"]),
    ("AIatMeta",       "Meta AI",             1, ["ai", "open_source"]),
    ("mistralai",      "Mistral AI",          2, ["ai", "open_source"]),
    ("xai",            "xAI / Grok",          2, ["ai", "model_release"]),
    ("karpathy",       "Andrej Karpathy",     1, ["ai", "education", "research"]),
    ("ylecun",         "Yann LeCun",          2, ["ai", "research"]),
    ("andrewyng",      "Andrew Ng",           2, ["ai", "education"]),
    ("fchollet",       "François Chollet",    2, ["ai", "research"]),
    ("demishassabis",  "Demis Hassabis",      2, ["ai", "research"]),
    ("LangChainAI",    "LangChain",           2, ["ai", "tools", "open_source"]),
    ("huggingface",    "Hugging Face",        1, ["ai", "open_source", "models"]),
    ("nvidia",         "NVIDIA",              2, ["hardware", "ai"]),
    ("perplexity_ai",  "Perplexity AI",       3, ["ai", "product"]),
    ("elonmusk",       "Elon Musk",           2, ["tech", "industry"]),
    ("satyanadella",   "Satya Nadella",       3, ["tech", "industry"]),
    ("sundarpichai",   "Sundar Pichai",       3, ["tech", "industry"]),
]


def build_nitter_sources() -> list[Source]:
    sources = []
    instance = NITTER_INSTANCES[0]
    for username, label, priority, tags in NITTER_ACCOUNTS:
        sources.append(Source(
            key=f"nitter_{username.lower()}",
            label=f"@{username} ({label})",
            type="nitter",
            url=f"https://{instance}/{username}/rss",
            priority=priority,
            tags=tags,
        ))
    return sources


RSS_SOURCES = [
    Source("rss_techcrunch_ai",   "TechCrunch AI",        "rss",
           "https://techcrunch.com/category/artificial-intelligence/feed/", 1,
           ["ai", "product_launch", "funding"]),
    Source("rss_theverge",        "The Verge",             "rss",
           "https://www.theverge.com/rss/index.xml", 2,
           ["tech", "product"]),
    Source("rss_arstechnica",     "Ars Technica",          "rss",
           "https://feeds.arstechnica.com/arstechnica/index", 2,
           ["tech", "science", "research"]),
    Source("rss_mit_techreview",  "MIT Technology Review", "rss",
           "https://www.technologyreview.com/feed/", 1,
           ["ai", "research", "policy"]),
    Source("rss_wired",           "Wired",                 "rss",
           "https://www.wired.com/feed/rss", 2,
           ["tech", "culture"]),
    Source("rss_nyt_tech",        "NYT Technology",        "rss",
           "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml", 2,
           ["tech", "policy"]),
    Source("rss_venturebeat_ai",  "VentureBeat AI",        "rss",
           "https://venturebeat.com/category/ai/feed/", 2,
           ["ai", "funding", "product"]),
    Source("rss_openai_blog",     "OpenAI Blog",           "rss",
           "https://openai.com/blog/rss.xml", 1,
           ["ai", "research", "model_release"]),
    Source("rss_anthropic_blog",  "Anthropic Blog",        "rss",
           "https://www.anthropic.com/rss.xml", 1,
           ["ai", "safety", "research"]),
    Source("rss_google_ai_blog",  "Google AI Blog",        "rss",
           "https://blog.google/technology/ai/rss/", 1,
           ["ai", "research"]),
    Source("rss_deepmind_blog",   "DeepMind Blog",         "rss",
           "https://deepmind.google/blog/rss.xml", 1,
           ["ai", "research"]),
    Source("rss_huggingface",     "Hugging Face Blog",     "rss",
           "https://huggingface.co/blog/feed.xml", 1,
           ["ai", "open_source", "models"]),
]

YOUTUBE_CHANNELS = [
    Source("youtube_openai",       "OpenAI YouTube",        "youtube",
           "UCXZCJLdBC09xxGZ6gcdrc6A", 1, ["ai", "tutorial"]),
    Source("youtube_andrejk",      "Andrej Karpathy",       "youtube",
           "UCBcRF18a7Qf58cCRy5xuWwQ", 1, ["ai", "education"]),
    Source("youtube_google_deepmind", "Google DeepMind",    "youtube",
           "UCP7jMXSY2xbc3KCAE0MHQ-A", 1, ["ai", "research"]),
    Source("youtube_huggingface",  "Hugging Face",          "youtube",
           "UCHlnu08TIyElYlsdslzAike", 2, ["ai", "tutorial"]),
    Source("youtube_matt_wolfe",   "Matt Wolfe",            "youtube",
           "UCKBq3-_1YjCwdvCdoMNi4Nw", 2, ["ai", "news"]),
]

GITHUB_REPOS = [
    Source("github_langchain",    "LangChain releases",    "github",
           "langchain-ai/langchain", 2, ["ai", "open_source"]),
    Source("github_ollama",       "Ollama releases",       "github",
           "ollama/ollama", 2, ["ai", "open_source"]),
    Source("github_llama_cpp",    "llama.cpp releases",    "github",
           "ggerganov/llama.cpp", 2, ["ai", "open_source"]),
    Source("github_transformers", "HuggingFace Transformers", "github",
           "huggingface/transformers", 1, ["ai", "open_source"]),
    Source("github_autogen",      "AutoGen releases",      "github",
           "microsoft/autogen", 2, ["ai", "agents"]),
    Source("github_crewai",       "CrewAI releases",       "github",
           "crewAIInc/crewAI", 3, ["ai", "agents"]),
]

REDDIT_SOURCES = [
    Source("reddit_ml",           "r/MachineLearning",     "reddit",
           "MachineLearning", 1, ["ai", "research"]),
    Source("reddit_artificial",   "r/artificial",          "reddit",
           "artificial", 3, ["ai", "news"]),
    Source("reddit_localllama",   "r/LocalLLaMA",          "reddit",
           "LocalLLaMA", 2, ["ai", "open_source"]),
    Source("reddit_openai",       "r/OpenAI",              "reddit",
           "OpenAI", 2, ["ai", "product"]),
    Source("reddit_technology",   "r/technology",          "reddit",
           "technology", 3, ["tech", "news"]),
]

HN_SOURCES = [
    Source("hn_top",              "HackerNews Top",        "hackernews",
           "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=20", 2,
           ["tech", "startup"]),
    Source("hn_ai",               "HackerNews AI stories", "hackernews",
           "https://hn.algolia.com/api/v1/search?query=AI+LLM+GPT&tags=story&hitsPerPage=15", 2,
           ["ai", "tech"]),
]

LINKEDIN_PAGES = [
    Source("linkedin_openai",     "OpenAI LinkedIn",       "linkedin_scrape",
           "https://www.linkedin.com/company/openai/posts/", 2, ["ai"]),
    Source("linkedin_anthropic",  "Anthropic LinkedIn",    "linkedin_scrape",
           "https://www.linkedin.com/company/anthropic-ai/posts/", 2, ["ai"]),
    Source("linkedin_google_deepmind", "DeepMind LinkedIn", "linkedin_scrape",
           "https://www.linkedin.com/company/googledeepmind/posts/", 2, ["ai"]),
    Source("linkedin_huggingface","Hugging Face LinkedIn", "linkedin_scrape",
           "https://www.linkedin.com/company/huggingface/posts/", 2, ["ai"]),
]


def get_all_sources() -> list[Source]:
    return (
        RSS_SOURCES
        + build_nitter_sources()
        + YOUTUBE_CHANNELS
        + GITHUB_REPOS
        + REDDIT_SOURCES
        + HN_SOURCES
        + LINKEDIN_PAGES
    )
