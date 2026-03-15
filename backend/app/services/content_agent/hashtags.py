"""Hashtag generator — curated packs by category + platform."""
from __future__ import annotations

HASHTAG_PACKS: dict[str, dict[str, list[str]]] = {
    "model_release": {
        "instagram": ["#AIModelRelease", "#NewAI", "#ArtificialIntelligence", "#MachineLearning",
            "#DeepLearning", "#AINews", "#TechNews", "#OpenAI", "#Gemini", "#Claude",
            "#LLM", "#GenerativeAI", "#AIUpdates", "#FutureOfAI", "#TechIndia",
            "#AIRevolution", "#NeuralNetwork", "#AITools", "#AITrends", "#Innovation"],
        "linkedin": ["#ArtificialIntelligence", "#MachineLearning", "#AIInnovation",
            "#GenerativeAI", "#TechLeadership", "#AIStrategy", "#FutureOfWork", "#LLM"],
        "twitter": ["#AI", "#LLM", "#GenerativeAI", "#AINews", "#MachineLearning"],
    },
    "research_paper": {
        "instagram": ["#AIResearch", "#MachineLearning", "#DeepLearning", "#Research",
            "#ArtificialIntelligence", "#NeuralNetwork", "#ComputerScience", "#AIScience",
            "#TechResearch", "#AIBreakthrough", "#MLPaper", "#AIDiscovery", "#Science",
            "#TechNews", "#FutureOfAI"],
        "linkedin": ["#AIResearch", "#MachineLearning", "#DeepLearning", "#AcademicAI",
            "#ResearchAndDevelopment", "#Innovation", "#TechInnovation", "#DataScience"],
        "twitter": ["#AIResearch", "#MLPaper", "#DeepLearning", "#AI", "#NeurIPS"],
    },
    "open_source": {
        "instagram": ["#OpenSource", "#GitHub", "#Coding", "#Developer", "#Programming",
            "#OpenSourceAI", "#HuggingFace", "#LangChain", "#AITools", "#DevCommunity",
            "#TechCommunity", "#BuildInPublic", "#AIForAll", "#FreeAI", "#IndianDev"],
        "linkedin": ["#OpenSource", "#GitHub", "#DeveloperCommunity", "#OpenSourceAI",
            "#SoftwareDevelopment", "#AITools", "#BuildInPublic", "#TechCommunity"],
        "twitter": ["#OpenSource", "#GitHub", "#DevCommunity", "#BuildInPublic", "#AI"],
    },
    "product_launch": {
        "instagram": ["#ProductLaunch", "#NewTech", "#AIProduct", "#TechLaunch", "#Innovation",
            "#ArtificialIntelligence", "#TechNews", "#AITools", "#FutureOfTech",
            "#TechUpdate", "#AIStartup", "#TechIndia", "#DigitalIndia", "#Startup", "#ProductHunt"],
        "linkedin": ["#ProductLaunch", "#Innovation", "#TechProduct", "#AIBusiness",
            "#DigitalTransformation", "#Startup", "#TechLeadership", "#ProductManagement"],
        "twitter": ["#ProductLaunch", "#AI", "#TechNews", "#Innovation", "#NewTech"],
    },
    "funding": {
        "instagram": ["#StartupFunding", "#VentureCapital", "#AIStartup", "#TechStartup",
            "#Fundraising", "#Investment", "#AIFunding", "#TechInvestment", "#Startup",
            "#VC", "#AngelInvesting", "#TechBusiness", "#Innovation", "#TechNews", "#IndianStartup"],
        "linkedin": ["#VentureCapital", "#StartupFunding", "#AIStartup", "#Investment",
            "#Entrepreneurship", "#TechInvestment", "#StartupEcosystem", "#VC"],
        "twitter": ["#Funding", "#VC", "#AIStartup", "#TechNews", "#Startup"],
    },
    "tutorial": {
        "instagram": ["#AITutorial", "#LearnAI", "#AIForBeginners", "#TechTutorial", "#HowTo",
            "#ArtificialIntelligence", "#MachineLearning", "#AIExplained", "#LearnToCode",
            "#TechEducation", "#AISimplified", "#DigitalSkills", "#UpskillWithAI",
            "#TechIndia", "#AIIndia"],
        "linkedin": ["#AIEducation", "#LearnAI", "#SkillDevelopment", "#TechLearning",
            "#ProfessionalDevelopment", "#AIForProfessionals", "#DigitalSkills", "#Upskilling"],
        "twitter": ["#LearnAI", "#AITutorial", "#Coding", "#TechEd", "#AI"],
    },
    "industry_news": {
        "instagram": ["#TechNews", "#AINews", "#Technology", "#Innovation", "#FutureTech",
            "#ArtificialIntelligence", "#TechUpdate", "#BreakingTech", "#TechWorld",
            "#AIWorld", "#TechTrends", "#DigitalFuture", "#TechIndia", "#AIIndia", "#GlobalTech"],
        "linkedin": ["#TechNews", "#IndustryNews", "#TechTrends", "#DigitalTransformation",
            "#Innovation", "#TechLeadership", "#FutureOfTechnology", "#AIIndustry"],
        "twitter": ["#TechNews", "#AI", "#Innovation", "#Tech", "#Breaking"],
    },
    "opinion_take": {
        "instagram": ["#AIOpinion", "#TechThoughts", "#AIDebate", "#FutureOfAI", "#AIEthics",
            "#TechPerspective", "#AIViews", "#ThoughtLeadership", "#TechInsights",
            "#AIDiscussion", "#TechTalk", "#AIConversation", "#DigitalAge", "#TechCulture",
            "#AIPhilosophy"],
        "linkedin": ["#ThoughtLeadership", "#AIOpinion", "#TechInsights", "#FutureOfWork",
            "#AIEthics", "#Innovation", "#Leadership", "#TechStrategy"],
        "twitter": ["#AIEthics", "#FutureOfAI", "#TechOpinion", "#AI", "#ThoughtLeadership"],
    },
    "other": {
        "instagram": ["#Technology", "#ArtificialIntelligence", "#Innovation", "#TechNews",
            "#MachineLearning", "#DigitalFuture", "#TechTrends", "#AIUpdate",
            "#TechCommunity", "#FutureTech", "#TechIndia", "#AIIndia",
            "#DigitalIndia", "#TechCreator", "#AIContent"],
        "linkedin": ["#Technology", "#Innovation", "#ArtificialIntelligence",
            "#DigitalTransformation", "#TechTrends", "#FutureOfWork"],
        "twitter": ["#Tech", "#AI", "#Innovation", "#Technology", "#News"],
    },
}

INDIA_HASHTAGS = {
    "instagram": ["#TechIndia", "#AIIndia", "#IndianTech", "#MakeInIndia", "#DigitalIndia"],
    "linkedin": ["#IndianTech", "#TechIndia", "#StartupIndia", "#DigitalIndia"],
    "twitter": ["#TechIndia", "#AIIndia"],
}


def get_hashtags(category: str, platform: str, include_india: bool = True, count: int = 20) -> list[str]:
    platform_key = platform if platform in ("instagram", "linkedin", "twitter") else "instagram"
    pack = HASHTAG_PACKS.get(category, HASHTAG_PACKS["other"])
    hashtags = list(pack.get(platform_key, pack["instagram"]))
    if include_india:
        for tag in INDIA_HASHTAGS.get(platform_key, []):
            if tag not in hashtags:
                hashtags.insert(3, tag)
    return hashtags[:count]


def format_hashtags(hashtags: list[str], as_string: bool = False) -> str | list[str]:
    formatted = [h if h.startswith("#") else f"#{h}" for h in hashtags]
    if as_string:
        return " ".join(formatted)
    return formatted
