faq_data = [
    {
        "questions": [
            "What is this AI?",
            "What are you?",
            "Who are you?",
            "Explain yourself",
            "What does this assistant do?",
            "What is your purpose?"
        ],
        "answer": """
        <p>👋 Hi! I'm a specialized <strong>Math Assistant</strong>, built to help you solve basic to intermediate math problems and understand concepts.</p>
        <p>My main capabilities include:</p>
        <ul>
            <li>🧮 <strong>Algebra:</strong> Solving single-variable and systems of equations (e.g., <code>2x + 3 = 7</code> or <code>x + y = 5, x - y = 1</code>) with detailed steps.</li>
            <li>🔢 <strong>Number Theory:</strong> Calculating HCF (Highest Common Factor) and LCM (Least Common Multiple) for multiple integers.</li>
            <li>✂️ <strong>Simplification:</strong> Reducing complex algebraic expressions and arithmetic problems.</li>
        </ul>
        """
    },
    {
        "questions": [
            "How does this AI work?",
            "How do you function?",
            "How are you made?",
            "Is this a large language model?",
            "HOw do you work?"
        ],
        "answer": """
        <p>⚙️ I operate on a <strong>rule-based engine</strong>, not a traditional generative Large Language Model (LLM).</p>
        <p>My core functionality relies on:</p>
        <ul>
            <li>📐 <strong>Math Parsers:</strong> Using libraries like SymPy to accurately process and solve equations.</li>
            <li>🧩 <strong>Predefined Rules:</strong> Specific algorithms for HCF/LCM and step-by-step algebra.</li>
            <li>❓ <strong>FAQ Matching:</strong> Using a fuzzy matching system to answer common non-math questions.</li>
        </ul>
        <p>This approach ensures accurate, deterministic math results.</p>
        """
    },
    {
        "questions": [
            "How do I solve an algebra equation?",
            "Can you solve equations?",
            "Can you do systems of equations?",
            "How do I write an expression?"
        ],
        "answer": """
        <p>📘 I can solve single equations and systems of two equations.</p>
        <h4>Single Equation:</h4>
        <p>Type the equation with one variable (e.g., <code>x</code>):<br>
        Example: <code>4x + 12 = 2x - 6</code></p>
        <h4>System of Equations (2 variables):</h4>
        <p>Separate the two equations with a comma:<br>
        Example: <code>2x + y = 10, x - y = 5</code></p>
        <h4>Expression Simplification:</h4>
        <p>Type the expression without an equals sign:<br>
        Example: <code>3x + 5y - 7x + 2</code></p>
        """
    },
    {
        "questions": [
            "How do I calculate HCF or LCM?",
            "HCF of what?",
            "LCM of what?"
        ],
        "answer": """
        <p>🔢 To calculate HCF or LCM, specify the operation and the numbers, separated by commas or spaces.</p>
        <ul>
            <li>HCF Example: <code>HCF of 12, 18, 30</code></li>
            <li>LCM Example: <code>LCM 4, 6, 8</code></li>
        </ul>
        <p>You can also use <code>GCD</code> instead of HCF.</p>
        """
    },
    {
        "questions": [
            "What are your limitations?",
            "What can't you do?",
            "Are there any restrictions?"
        ],
        "answer": """
        <p>⚠️ I have a few important limitations:</p>
        <ul>
            <li>🔢 <strong>Integers Only:</strong> I work primarily with integer coefficients and integer solutions. Fractions or decimals may give unexpected results.</li>
            <li>📚 <strong>Complexity:</strong> I cannot handle advanced topics like calculus, complex numbers, differential equations, or functions like sin, cos, log, etc.</li>
            <li>📝 <strong>Formatting:</strong> Ensure all equations are on a single line for accurate processing.</li>
        </ul>
        """
    },
    {
        "questions": [
            "Do you save chats?",
            "Can I open old chats?",
            "Does it remember?",
            "Is my data private?"
        ],
        "answer": """
        <p>💾 Your chat history is saved locally in your browser using <code>localStorage</code>.</p>
        <p>This means all chats are private on your device—I do not send or store your history on any external server. You can open, rename, or delete old chats anytime.</p>
        """
    },
    {
        "questions": [
            "How do you give different answers?",
            "Why are your answers different each time?"
        ],
        "answer": """
        <p>🎲 For general (non-math) questions, I have multiple pre-written replies. I randomly select one each time, so the answer may vary slightly while keeping the meaning consistent.</p>
        """
    },
    {
        "questions": [
            "Fallback"
        ],
        "answer": """
        <p>🤷 I'm sorry, I don't know the answer to that. Please try asking a specific math question (like an equation or HCF/LCM query) or rephrase your question.</p>
        """
    }
]