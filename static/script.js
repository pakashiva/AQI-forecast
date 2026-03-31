function plotChart(canvasId, data) {

    const canvas = document.getElementById(canvasId);

    canvas.style.display = 'block';

    const ctx = document.getElementById(canvasId).getContext("2d");

    // Destroy old chart if exists (important!)
    if (window[canvasId + "Instance"]) {
        window[canvasId + "Instance"].destroy();
    }

    // Build datasets dynamically
    let datasets = [
        {
            label: "Forecast",
            data: data.values,
            borderWidth: 2,
            tension: 0.3
        }
    ];

    // Add confidence intervals ONLY if present (SARIMAX case)
    if (data.upper && data.lower) {
        datasets.push(
            {
                label: "Upper Bound",
                data: data.upper,
                borderDash: [5, 5]
            },
            {
                label: "Lower Bound",
                data: data.lower,
                borderDash: [5, 5]
            }
        );
    }

    // Create chart instance
    window[canvasId + "Instance"] = new Chart(ctx, {
        type: "line",
        data: {
            labels: data.dates,
            datasets: datasets
        },
        options: {
            responsive: true
        }
    }); 
}