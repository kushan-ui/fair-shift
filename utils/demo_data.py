"""
FAIRSHIFT Synthetic Demo Dataset Generator
Creates 200 synthetic applicants, 10 training programs, ranked preferences,
and realistic eligibility profiles to illustrate real-world optimization scenarios.
"""

import random
from typing import List, Dict, Any, Tuple
from models.applicant import Applicant, Preference
from models.program import Program

PROGRAM_DEFINITIONS = [
    {
        "id": "PROG-AI",
        "name": "Advanced Machine Learning & Applied AI",
        "description": "Intensive cohort on deep learning, transformer architectures, and ML deployment.",
        "capacity": 22,
        "required_attributes": ["STEM"]
    },
    {
        "id": "PROG-CYBER",
        "name": "Cybersecurity Operations & Threat Defense",
        "description": "Hands-on cyber warfare defense, SOC operations, and penetration testing.",
        "capacity": 18,
        "required_attributes": ["SECURITY_CLEARANCE", "STEM"]
    },
    {
        "id": "PROG-CLOUD",
        "name": "Cloud Architecture & DevOps Systems",
        "description": "Multi-cloud infrastructure, Kubernetes orchestration, and continuous delivery.",
        "capacity": 25,
        "required_attributes": ["STEM"]
    },
    {
        "id": "PROG-DATA",
        "name": "Data Science & Business Analytics",
        "description": "Large-scale exploratory data analysis, statistical modeling, and data pipelines.",
        "capacity": 20,
        "required_attributes": ["STEM"]
    },
    {
        "id": "PROG-BIO",
        "name": "Computational Biology & Genomics",
        "description": "Genomic sequence modeling, protein structure informatics, and bio-pipelines.",
        "capacity": 15,
        "required_attributes": ["STEM", "LIFE_SCIENCES"]
    },
    {
        "id": "PROG-FIN",
        "name": "Quantitative Finance & Algorithmic Trading",
        "description": "Financial mathematics, derivative pricing, and high-frequency algorithms.",
        "capacity": 16,
        "required_attributes": ["FINANCE_MATH"]
    },
    {
        "id": "PROG-MGMT",
        "name": "Agile Technology Product Management",
        "description": "Product strategy, roadmap delivery, user research, and executive communication.",
        "capacity": 22,
        "required_attributes": []
    },
    {
        "id": "PROG-UX",
        "name": "Human-Centered Design & UX Engineering",
        "description": "Design systems, accessibility auditing, usability benchmarking, and rapid UI.",
        "capacity": 18,
        "required_attributes": []
    },
    {
        "id": "PROG-FULLSTACK",
        "name": "Enterprise Full-Stack Web Engineering",
        "description": "Distributed web architecture, microservices, database scaling, and frontend.",
        "capacity": 24,
        "required_attributes": []
    },
    {
        "id": "PROG-ENV",
        "name": "Clean Energy Systems & Climate Analytics",
        "description": "Decarbonization data modeling, solar/wind grid analytics, and resource forecasting.",
        "capacity": 15,
        "required_attributes": ["ENVIRONMENTAL_SCI"]
    }
]

FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Sam", "Pat", "Chris", "Jamie",
    "Avery", "Cameron", "Quinn", "Skyler", "Rowan", "Hayden", "Logan", "Reese", "Harper", "Kai",
    "Priya", "Elena", "Marcus", "Siddharth", "Amina", "Mateo", "Chloe", "Devon", "Liam", "Sofia",
    "Kenji", "Fatima", "Chen", "Leila", "Dante", "Nadia", "Carlos", "Mei", "Rashid", "Zara"
]

LAST_NAMES = [
    "Vance", "Chen", "O'Connor", "Kim", "Patel", "Rodriguez", "Smith", "Johnson", "Williams", "Muller",
    "Novak", "Gupta", "Abe", "Larsson", "Dubois", "Santos", "Tanaka", "Fischer", "Kowalski", "Bello",
    "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson", "Garcia", "Martinez"
]

def generate_demo_programs() -> List[Program]:
    programs = []
    for p in PROGRAM_DEFINITIONS:
        programs.append(Program(
            id=p["id"],
            name=p["name"],
            description=p["description"],
            capacity=p["capacity"],
            required_attributes=list(p["required_attributes"]),
            is_active=True
        ))
    return programs

def generate_demo_applicants(count: int = 200, seed: int = 42) -> List[Applicant]:
    rng = random.Random(seed)
    program_ids = [p["id"] for p in PROGRAM_DEFINITIONS]

    applicants: List[Applicant] = []

    for i in range(1, count + 1):
        app_id = f"APP-{i:03d}"
        fn = rng.choice(FIRST_NAMES)
        ln = rng.choice(LAST_NAMES)
        full_name = f"{fn} {ln}"
        email = f"{fn.lower()}.{ln.lower()}{i}@example.org"

        # Generate realistic eligibility tags
        attrs = []
        if rng.random() < 0.65:
            attrs.append("STEM")
        if rng.random() < 0.20:
            attrs.append("SECURITY_CLEARANCE")
        if rng.random() < 0.15:
            attrs.append("LIFE_SCIENCES")
        if rng.random() < 0.18:
            attrs.append("FINANCE_MATH")
        if rng.random() < 0.12:
            attrs.append("ENVIRONMENTAL_SCI")
        if rng.random() < 0.10:
            attrs.append("VETERAN")

        # Set 3 to 5 ranked preferences
        num_prefs = rng.randint(3, 5)
        # Give higher weight to popular programs like PROG-AI and PROG-CYBER
        weights = [3.0 if pid in ("PROG-AI", "PROG-CYBER", "PROG-FULLSTACK") else 1.0 for pid in program_ids]

        chosen_programs = []
        available = list(program_ids)
        available_w = list(weights)

        for _ in range(num_prefs):
            chosen = rng.choices(available, weights=available_w, k=1)[0]
            idx = available.index(chosen)
            available.pop(idx)
            available_w.pop(idx)
            chosen_programs.append(chosen)

        prefs = [Preference(program_id=pid, preference_rank=rank + 1) for rank, pid in enumerate(chosen_programs)]

        # Simulate a few withdrawals (e.g. 5 applicants)
        is_withdrawn = (i in (14, 42, 88, 125, 177))
        status = "WITHDRAWN" if is_withdrawn else "ACTIVE"

        applicants.append(Applicant(
            id=app_id,
            full_name=full_name,
            email=email,
            eligibility_attributes=attrs,
            status=status,
            is_withdrawn=is_withdrawn,
            preferences=prefs
        ))

    return applicants
