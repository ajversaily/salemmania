
const CelestialOracle = {
    elements: {
        Fire:  ["Aries", "Leo", "Sagittarius"],
        Earth: ["Taurus", "Virgo", "Capricorn"],
        Air:   ["Gemini", "Libra", "Aquarius"],
        Water: ["Cancer", "Scorpio", "Pisces"]
    },

    archetypes: {
        Fire: {
            role: "The Torchbearer",
            advice: "Your spirit is a flare in the dark. You are mandated to illuminate the 'Forge' and drive the conflict forward.",
            interference: "92%"
        },
        Earth: {
            role: "The Scribe",
            advice: "Grounded and unwavering. The Tribunal relies on your ability to record the weight of our shared history in the Archives.",
            interference: "45%"
        },
        Air: {
            role: "The Whisperer",
            advice: "You travel through the static. Your role is to spread interference where the establishment is most rigid.",
            interference: "78%"
        },
        Water: {
            role: "The Occultist",
            advice: "Deep waters hide deep secrets. You are the keeper of the unspoken 'Mania' and the curator of our shadows.",
            interference: "61%"
        }
    },

    initiateAlignment: function() {
        const sun = document.getElementById('sunSign').value;
        const moon = document.getElementById('moonSign').value;
        const rising = document.getElementById('risingSign').value;
        const resultDiv = document.getElementById('divination-output');
        const btn = document.querySelector('.audit-btn');

        btn.innerText = "ALIGNING...";
        btn.style.opacity = "0.5";

        let userElement = "";
        for (const [element, signs] in Object.entries(this.elements)) {
            if (this.elements[element].includes(sun)) {
                userElement = element;
                break;
            }

        const data = this.archetypes[userElement];
        setTimeout(() => {
            document.getElementById('res-sun').innerText = sun.toUpperCase();
            document.getElementById('res-moon').innerText = moon.toUpperCase();
            document.getElementById('res-rising').innerText = rising.toUpperCase();
            document.getElementById('res-insight').innerText = data.advice;
                        resultDiv.style.display = 'block'; 
            this.triggerInterference();

            btn.innerText = "ALIGNED";
            btn.style.opacity = "1";
        }, 800);
    },

    triggerInterference: function() {
        const originalBg = document.body.style.backgroundColor;
        document.body.style.transition = "background 0.1s";
        document.body.style.backgroundColor = "#c8002a";
        
        setTimeout(() => {
            document.body.style.backgroundColor = originalBg || "#080603";
            const container = document.querySelector('.audit-container');
            container.style.transform = "translateX(5px)";
            setTimeout(() => container.style.transform = "translateX(-5px)", 50);
            setTimeout(() => container.style.transform = "translateX(0)", 100);
        }, 100);
};function performRitual() {
    CelestialOracle.initiateAlignment();}
