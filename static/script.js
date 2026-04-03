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
            borderWidth: 3,
            borderColor: "rgba(32, 31, 27, 0.57)",
            tension: 0.3
        }
    ];

    // Add confidence intervals ONLY if present (SARIMAX case)
    if (data.upper && data.lower) {
        datasets.push(
            {
                label: "Upper Bound",
                data: data.upper,
                borderColor: "rgba(74, 74, 157, 0.82)",
                borderDash: [5, 5],
                fill: false

            },
            {
                label: "Lower Bound",
                data: data.lower,
                borderColor: "rgba(74, 74, 157, 0.82)",
                borderDash: [5, 5],
                fill: '-1', // fill to previous dataset (Upper Bound)
                backgroundColor: "rgba(255, 166, 0, 0.2)" // alpha = 0.3
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