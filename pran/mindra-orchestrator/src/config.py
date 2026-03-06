"""Agent registry and configuration."""

# Buyer API key (the wallet that pays for everything)
BUYER_NVM_API_KEY = "sandbox:eyJhbGciOiJFUzI1NksifQ.eyJpc3MiOiIweDZCMTZEMGIzMzQ4MjQ1ODFCNGEyNEE0OUZkN2ZjYkQ2NTA5Q0U1ZGEiLCJzdWIiOiIweGI0NEFhNjFGQUQwZTZGZUE1ZGJCNTRGZTg3ODFkMWQ3NTZDNDk5NjEiLCJqdGkiOiIweDc3NDY3NzBhODYyY2JhZGZlMWE2ZDJlN2ZlMjJhZmQ5M2U4NGJmYjE2MjJjOGVmZmYwODc3NWZiNGU5M2RlMTciLCJleHAiOjQ5Mjg1MDcxNTYsIm8xMXkiOiJzay1oZWxpY29uZS10cW5vNjRxLXl4NmVxcnEtdHBqeXJpcS1ybHY3aHVpIn0.cuq9tI9dAmuv8Iy_M-TNI_7HTO8KPEGskbmSCzJfVyhqo81Ip9_bj-OlxonysZPqQZ8WcO4qXfd4qjCfBGYn4Bw"

PLAN_ID = "62132339823439076950399695238634927378738244877172775303591114485168828025410"

# All leaf agents on Trinity with their Nevermined agent IDs
AGENTS = {
    "researcher": {
        "agent_id": "102575793179870454885693749389321147500444253017787287080547662366660764018939",
        "endpoint": "https://us14.abilityai.dev/api/paid/researcher/chat",
        "credits": 1,
        "role": "Web research and fact-finding",
    },
    "social-monitor": {
        "agent_id": "102575793179870454885693749389321147500444253017787287080547662366660764018939",
        "endpoint": "https://us14.abilityai.dev/api/paid/social-monitor/chat",
        "credits": 2,
        "role": "Social media monitoring and OSINT",
    },
    "nexus": {
        "agent_id": "38193170898726307123033205989462035601957241449542699022794362936331517059909",
        "endpoint": "https://us14.abilityai.dev/api/paid/nexus/chat",
        "credits": 1,
        "role": "Data analysis, competitive intelligence, technical advisory",
    },
    "writer": {
        "agent_id": "739071533822469363454794813167578815978480755573494968808789634091211405280",
        "endpoint": "https://us14.abilityai.dev/api/paid/writer/chat",
        "credits": 1,
        "role": "Content generation - reports, articles, copy",
    },
    "qa-checker": {
        "agent_id": "34717900564144577384221620768773912527087254723894341195443997683755291677420",
        "endpoint": "https://us14.abilityai.dev/api/paid/qa-checker/chat",
        "credits": 1,
        "role": "Fact-checking, quality assurance, validation",
    },
}

# Orchestrator routing
DEPARTMENTS = {
    "research": {
        "agents": ["researcher", "social-monitor"],
        "description": "Research department - web search, social monitoring, data gathering",
    },
    "production": {
        "agents": ["writer", "qa-checker"],
        "description": "Production department - content creation and quality assurance",
    },
    "analysis": {
        "agents": ["nexus"],
        "description": "Analysis department - data analysis, competitive intel, technical advisory",
    },
}
