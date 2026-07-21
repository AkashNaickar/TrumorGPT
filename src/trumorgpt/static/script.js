// Initialize Mermaid.js with Cognee dark grid styling
mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    themeVariables: {
        darkMode: true,
        background: '#000000',
        primaryColor: '#09090B',
        primaryBorderColor: '#A78BFA',
        primaryTextColor: '#ECECEE',
        lineColor: '#71717A'
    }
});

function fillClaim(text) {
    document.getElementById('claimInput').value = text;
    executeFactCheck();
}

async function executeFactCheck() {
    const claimInput = document.getElementById('claimInput').value.trim();
    if (!claimInput) {
        alert("Please enter a health claim or news text to fact-check.");
        return;
    }

    const submitBtn = document.getElementById('submitBtn');
    const btnText = document.getElementById('btnText');
    const btnSpinner = document.getElementById('btnSpinner');
    const resultsSection = document.getElementById('resultsSection');

    // UI Loading State
    submitBtn.disabled = true;
    btnText.classList.add('hidden');
    btnSpinner.classList.remove('hidden');

    try {
        const response = await fetch('/api/v1/fact-check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: claimInput })
        });

        if (!response.ok) {
            throw new Error(`API returned status ${response.status}`);
        }

        const data = await response.json();
        renderFactCheckResult(data);
        resultsSection.classList.remove('hidden');
        resultsSection.scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        alert("Error performing fact-check: " + error.message);
    } finally {
        submitBtn.disabled = false;
        btnText.classList.remove('hidden');
        btnSpinner.classList.add('hidden');
    }
}

function renderFactCheckResult(data) {
    const verdictBanner = document.getElementById('verdictBanner');
    const verdictBadge = document.getElementById('verdictBadge');
    const verdictImage = document.getElementById('verdictImage');
    const verdictExplanation = document.getElementById('verdictExplanation');

    // Reset verdict card classes
    verdictBanner.className = 'cognee-verdict-card';

    if (data.verdict === 'False') {
        verdictBanner.classList.add('verdict-false');
        verdictBadge.innerHTML = 'LIAR LIAR PANTS ON FIRE! 🔥';
        verdictImage.src = '/static/images/liar_pants_on_fire.png';
    } else if (data.verdict === 'True') {
        verdictBanner.classList.add('verdict-true');
        verdictBadge.innerHTML = 'VERIFIED TRUMOR — FACTUAL TRUTH 🛡️';
        verdictImage.src = '/static/images/verified_trumor_shield.png';
    } else {
        verdictBanner.classList.add('verdict-undetermined');
        verdictBadge.innerHTML = 'UNVERIFIED / UNCERTAIN CLAIM ❓';
        verdictImage.src = '/static/images/uncertain_claim_confused.png?v=1';
    }


    verdictExplanation.textContent = data.explanation;

    // Metrics
    document.getElementById('similarityScore').textContent = (data.metrics.accuracy_score || 0).toFixed(4);
    document.getElementById('tstIterations').textContent = `${data.metrics.tst_iterations || 1} iter (Converged)`;
    document.getElementById('extractionEngine').textContent = data.query_knowledge_graph.source || 'Ollama (LLaMA 3.1:8B)';

    // Topic badge
    const evidenceTopic = document.getElementById('evidenceTopic');
    if (data.evidence_knowledge_graph) {
        evidenceTopic.textContent = data.evidence_knowledge_graph.topic || 'Medical Guidelines';
    } else {
        evidenceTopic.textContent = 'No Direct Match';
    }

    // Render Mermaid Graphs
    renderMermaidGraph('queryMermaid', data.query_knowledge_graph, '#A78BFA');
    renderMermaidGraph('evidenceMermaid', data.evidence_knowledge_graph || { triples: [] }, '#34D399');
}

function renderMermaidGraph(containerId, graphData, strokeColor) {
    const container = document.getElementById(containerId);
    container.removeAttribute('data-processed');

    const triples = graphData.triples || [];
    if (triples.length === 0) {
        container.innerHTML = '<span style="color:#71717A; font-size:12px;">No graph triples available</span>';
        return;
    }

    let mermaidSyntax = `graph TD\n`;
    mermaidSyntax += `    classDef customNode fill:#09090B,stroke:${strokeColor},stroke-width:1.5px,color:#ECECEE,font-size:12px;\n`;

    triples.forEach((t, index) => {
        let h = sanitizeLabel(t.head);
        let r = sanitizeLabel(t.relation);
        let v = sanitizeLabel(t.tail);
        mermaidSyntax += `    N${index}_H["${h}"]:::customNode -->|"${r}"| N${index}_T["${v}"]:::customNode\n`;
    });

    mermaidSyntax += `    linkStyle default stroke:#71717A,stroke-width:1.5px;\n`;

    container.innerHTML = mermaidSyntax;
    mermaid.run({ nodes: [container] });
}

function sanitizeLabel(text) {
    return text.replace(/"/g, "'").replace(/\n/g, ' ');
}

function openSeederModal() {
    document.getElementById('seederModal').classList.remove('hidden');
}

function closeSeederModal() {
    document.getElementById('seederModal').classList.add('hidden');
}

async function submitSeedGraph() {
    const graph_id = document.getElementById('seedGraphId').value || 'kg_custom_' + Date.now();
    const topic = document.getElementById('seedTopic').value || 'Custom Health Fact';
    const head = document.getElementById('seedHead').value.trim();
    const relation = document.getElementById('seedRel').value.trim();
    const tail = document.getElementById('seedTail').value.trim();

    if (!head || !relation || !tail) {
        alert("Please fill in all triple fields (Head, Relation, Tail).");
        return;
    }

    const payload = {
        graph_id,
        source: "User Dynamic Seeder",
        topic,
        triples: [{ head, relation, tail }]
    };

    try {
        const response = await fetch('/api/v1/seed-graph', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            alert(`✅ Knowledge Graph '${topic}' successfully seeded into GraphRAG memory!`);
            closeSeederModal();
        } else {
            alert("Error seeding knowledge graph.");
        }
    } catch (e) {
        alert("Failed to seed knowledge graph: " + e.message);
    }
}

function copyTerminalCode() {
    const codeText = document.getElementById('curlCode').innerText;
    navigator.clipboard.writeText(codeText).then(() => {
        alert("cURL command copied to clipboard!");
    }).catch(err => {
        console.error('Failed to copy text: ', err);
    });
}
