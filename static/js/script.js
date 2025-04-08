document.addEventListener("DOMContentLoaded", function () {
    const loginForm = document.getElementById("loginForm");
    const loginSection = document.getElementById("loginSection");
    const mainTool = document.getElementById("mainTool");
    const loginResponse = document.getElementById("loginResponse");
    const logoutButton = document.getElementById("logoutButton");
    const loadLatestReportButton = document.getElementById("loadLatestReportButton");
    const calculateTotalSummaryButton = document.getElementById("calculateTotalSummaryButton");
    const contentDisplay = document.getElementById("contentDisplay");
    const generateReportGraphsButton = document.getElementById("generateReportGraphs");
    const generateNewReportsButton = document.getElementById("generateNewReportsButton");
    const completeReportButton = document.getElementById("completeReportButton");

    let currentGraphBlob = null;

    if (!loginForm) return;

    loginForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const username = document.getElementById("username").value.trim();
        const password = document.getElementById("password").value.trim();

        try {
            const response = await fetch("/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (data.error) {
                loginResponse.textContent = data.error;
                loginResponse.style.color = "red";
            } else {
                loginSection.style.display = "none";
                mainTool.style.display = "block";
                await fetchTotalSummary();
            }
        } catch (error) {
            loginResponse.textContent = "Network error. Please try again later.";
            loginResponse.style.color = "red";
        }
    });

    if (logoutButton) {
        logoutButton.addEventListener("click", async function () {
            const response = await fetch("/logout", { method: "POST" });
            const data = await response.json();
            if (data.message) {
                alert(data.message);
                location.reload();
            }
        });
    }

    if (generateReportGraphsButton) {
        generateReportGraphsButton.addEventListener("click", function () {
            contentDisplay.innerHTML = '';
            const loadingContainer = document.createElement("div");
            loadingContainer.classList.add("d-flex", "flex-column", "align-items-center", "justify-content-center", "mt-3");

            // Create spinner
            const loadingIndicator = document.createElement("div");
            loadingIndicator.classList.add("spinner-border", "text-primary");
            loadingIndicator.role = "status";

            // Create loading message
            const loadingMessage = document.createElement("div");
            loadingMessage.classList.add("mt-2", "fw-bold", "text-primary");
            loadingMessage.textContent = "Loading, please wait...";

            // Append elements
            loadingContainer.appendChild(loadingIndicator);
            loadingContainer.appendChild(loadingMessage);
            contentDisplay.appendChild(loadingContainer);

            fetch("/get_player_metrics_graphs", {
                method: "GET",
                headers: { "Content-Type": "application/json" }
            })
            .then(response => response.blob())
            .then(blob => {
                currentGraphBlob = blob;
                const imgElement = document.createElement("img");
                imgElement.src = URL.createObjectURL(blob);
                imgElement.alt = "Generated Report Graph";
                imgElement.style.maxWidth = "100%";
                imgElement.style.maxHeight = "1100px";
                contentDisplay.innerHTML = ""; // Clear existing content
                contentDisplay.appendChild(imgElement); // Display the graph

                // Create and append the Download button, positioned right above the graph
                const downloadButtonContainer = document.createElement("div");
                downloadButtonContainer.classList.add("text-end", "mb-2");  // Right-align and give margin below the button

                const downloadButton = document.createElement("button");
                downloadButton.textContent = "Download Graphs";
                downloadButton.classList.add("btn", "btn-success");  // Change button color to green

                downloadButton.addEventListener("click", function () {
                    const link = document.createElement("a");
                    link.href = imgElement.src;  // The image URL created from the blob
                    link.download = "generated_graph.png";  // Set the download file name
                    link.click();
                });

                downloadButtonContainer.appendChild(downloadButton);
                contentDisplay.insertBefore(downloadButtonContainer, imgElement);  // Insert above the graph

                // Remove loading indicator
                contentDisplay.removeChild(loadingContainer);
            })
            .catch(error => {
                console.error("Error generating report graphs:", error);
                if (loadingIndicator) loadingIndicator.style.display = "none";
            });
        });
    }

    if (calculateTotalSummaryButton) {
        calculateTotalSummaryButton.addEventListener("click", async function () {
            await fetchTotalSummary();
        });
    }

    if (generateNewReportsButton) {
        generateNewReportsButton.addEventListener("click", function () {
            // Create and display the file upload form dynamically if it's not already present
            const fileUploadForm = document.getElementById("fileUploadForm");
            if (!fileUploadForm) {
                const formHTML = `
                    <form id="fileUploadForm" style="display: block;">
                        <div class="mb-3">
                            <label for="fileInput" class="form-label">Select Files to Upload</label>
                            <input type="file" id="fileInput" class="form-control" multiple required>
                        </div>
                        <button type="submit" class="btn btn-primary">Upload Files</button>
                        <p id="uploadResponse" class="mt-2"></p>
                    </form>
                `;
                contentDisplay.innerHTML = `<h3 class="text-center">Upload Files</h3>` + formHTML;
            } else {
                fileUploadForm.style.display = "block";  // Show it if it already exists
            }

            // Handle form submission for file upload
            const fileUploadFormElement = document.getElementById("fileUploadForm");
            fileUploadFormElement.addEventListener("submit", async function(e) {
                e.preventDefault();
                const files = document.getElementById("fileInput").files;
                const formData = new FormData();
                for (const file of files) {
                    formData.append("files", file);
                }

                const response = await fetch("/generate_all_reports", {
                    method: "POST",
                    body: formData
                });
                const data = await response.json();
                document.getElementById("uploadResponse").textContent = data.message || data.error;
            });
        });
    }

    if (loadLatestReportButton) {
        loadLatestReportButton.addEventListener("click", async function () {
            try {
                const response = await fetch("/load_latest_data", { method: "GET" });
                const data = await response.json();

                if (data.error) {
                    alert(data.error);
                } else {
                    const contentDisplay = document.getElementById("contentDisplay");
                    if (contentDisplay) {
                        contentDisplay.style.display = "block";
                        contentDisplay.innerHTML = `
                            <h3 class="text-center">Latest Metrics</h3>
                                <table class="table table-bordered">
                                    <thead class="table-light">
                                        <tr>
                                            <th>Metrics</th>
                                            <th>Values (${data.metrics.latest_data})</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr><td>Total Bet</td><td>${data.metrics.total_bet}</td></tr>
                                        <tr><td>Total Win</td><td>${data.metrics.total_win}</td></tr>
                                        <tr><td>Reel Spins</td><td>${data.metrics.reel_spins}</td></tr>
                                        <tr><td>Social Spins</td><td>${data.metrics.social_spins}</td></tr>
                                        <tr><td>Total Spins</td><td>${data.metrics.total_spins}</td></tr>
                                        <tr><td>RTP (%)</td><td>${data.metrics.rtp}</td></tr>
                                        <tr><td>GGR (EUR)</td><td>${data.metrics.ggr_eur}</td></tr>
                                        <tr><td>GGR (GBP)</td><td>${data.metrics.ggr_gbp}</td></tr>
                                    </tbody>
                                </table>
                        `;
                    }
                }
            } catch (error) {
                console.error("Error loading latest data:", error);
                alert("An error occurred while loading the latest data.");
            }
        });
    }

   if (completeReportButton) {
        completeReportButton.addEventListener("click", async function () {
            try {
                // Clear previous content to prevent overlap
                contentDisplay.innerHTML = '';

                // Create loading indicator container
                const loadingContainer = document.createElement("div");
                loadingContainer.classList.add("d-flex", "flex-column", "align-items-center", "justify-content-center", "mt-3");

                // Create spinner
                const loadingIndicator = document.createElement("div");
                loadingIndicator.classList.add("spinner-border", "text-primary");
                loadingIndicator.role = "status";

                // Create loading message
                const loadingMessage = document.createElement("div");
                loadingMessage.classList.add("mt-2", "fw-bold", "text-primary");
                loadingMessage.textContent = "Loading, please wait...";

                // Append elements
                loadingContainer.appendChild(loadingIndicator);
                loadingContainer.appendChild(loadingMessage);
                contentDisplay.appendChild(loadingContainer);

                const response = await fetch("/calculate_total_summary", { method: "GET" });
                const data = await response.json();

                // Remove loading indicator
                contentDisplay.removeChild(loadingContainer);

                // Check if there's an error
                if (data.error) {
                    alert(data.error);
                    return;
                }

                // Create table for total summary
                const tableContainer = document.createElement("div");
                tableContainer.classList.add("table-responsive", "mt-3");

                const table = document.createElement("table");
                table.classList.add("table", "table-striped", "table-bordered", "text-center");

                // Table Header
                table.innerHTML = `
                    <thead class="table-dark">
                        <tr>
                            <th>Date</th>
                            <th>Total Bet</th>
                            <th>Total Win</th>
                            <th>Reel Spins</th>
                            <th style="width:100px;">Social Spins</th>
                            <th>Total Spins</th>
                            <th>RTP (%)</th>
                            <th>GGR (EUR)</th>
                            <th>GGR (GBP)</th>
                        </tr>
                    </thead>
                `;

                const tableBody = document.createElement("tbody");

                // Initialize totals
                let totalBet = 0, totalWin = 0, totalSpins = 0, totalSocialSpins = 0, totalReelSpins = 0;
                let totalGgrEur = 0, totalGgrGbp = 0;
                let minDate = null, maxDate = null;

                // Populate table rows
                Object.entries(data.data).forEach(([key, item]) => {
                    key = item.date;
                    const row = document.createElement("tr");
                    row.innerHTML = `
                        <td>${key}</td>
                        <td>${item.total_bet.toFixed(2)}</td>
                        <td>${item.total_win.toFixed(2)}</td>
                        <td>${item.reel_spins || 0}</td>
                        <td>${item.social_spins || 0}</td>
                        <td>${item.total_spins || 0}</td>
                        <td>${(item.rtp || 0).toFixed(2)}%</td>
                        <td>${item.ggr_eur.toFixed(2)}</td>
                        <td>${item.ggr_gbp.toFixed(2)}</td>
                    `;
                    tableBody.appendChild(row);

                    // Accumulate total values
                    totalBet += item.total_bet || 0;
                    totalWin += item.total_win || 0;
                    totalSpins += item.total_spins || 0;
                    totalSocialSpins += item.social_spins || 0;
                    totalReelSpins += item.reel_spins || 0;
                    totalGgrEur += item.ggr_eur || 0;
                    totalGgrGbp += item.ggr_gbp || 0;

                    if (!minDate || key < minDate) minDate = key;
                    if (!maxDate || key > maxDate) maxDate = key;
                });

                // Append rows to table
                table.appendChild(tableBody);
                tableContainer.appendChild(table);

                // Add the table container to the content display
                contentDisplay.appendChild(tableContainer);

                // Create and append the Copy button above the table, on the top-right
                const copyButtonContainer = document.createElement("div");
                copyButtonContainer.classList.add("text-end", "mb-2");  // Ensures the button is aligned to the right

                const copyButton = document.createElement("button");
                copyButton.textContent = "Copy To Clipboard";
                copyButton.classList.add("btn", "btn-secondary");

                copyButton.addEventListener("click", function () {
                    const tableText = table.innerText;
                    const textArea = document.createElement("textarea");
                    textArea.value = tableText;
                    document.body.appendChild(textArea);
                    textArea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textArea);
                    alert("Table data copied to clipboard!");
                });

                copyButtonContainer.appendChild(copyButton);
                contentDisplay.insertBefore(copyButtonContainer, tableContainer);

                // Calculate average RTP
                const avgRtp = totalBet > 0 ? (totalWin / totalBet) * 100 : 0;

                // Summary Section
                const totalSummaryDisplay = document.createElement("div");
                totalSummaryDisplay.classList.add("mt-3", "p-3", "border", "rounded", "bg-light");
                totalSummaryDisplay.innerHTML = `
                    <h4 class="text-center mb-3">Total Summary</h4>
                    <p><strong>Total Bet:</strong> ${totalBet.toFixed(2)}</p>
                    <p><strong>Total Win:</strong> ${totalWin.toFixed(2)}</p>
                    <p><strong>Total Spins:</strong> ${totalSpins}</p>
                    <p><strong>Social Spins:</strong> ${totalSocialSpins}</p>
                    <p><strong>Reel Spins:</strong> ${totalReelSpins}</p>
                    <p><strong>RTP:</strong> ${avgRtp.toFixed(2)}%</p>
                    <p><strong>GGR (EUR):</strong> ${totalGgrEur.toFixed(2)}</p>
                    <p><strong>GGR (GBP):</strong> ${totalGgrGbp.toFixed(2)}</p>
                `;

                // Download Button
                const downloadButton = document.createElement("button");
                downloadButton.textContent = "Download Report";
                downloadButton.classList.add("btn", "btn-primary", "mt-2");

                downloadButton.addEventListener("click", function () {
                    const tableData = [];
                    const headers = ["Date", "Total Bet", "Total Win", "Reel Spins", "Social Spins", "Total Spins", "RTP (%)", "GGR (EUR)", "GGR (GBP)"];
                    tableData.push(headers);

                    tableBody.querySelectorAll("tr").forEach(row => {
                        const cells = row.querySelectorAll("td");
                        const rowData = [];
                        cells.forEach(cell => rowData.push(cell.textContent));
                        tableData.push(rowData);
                    });

                    const worksheet = XLSX.utils.aoa_to_sheet(tableData);
                    const workbook = XLSX.utils.book_new();
                    XLSX.utils.book_append_sheet(workbook, worksheet, "Total Summary");

                    const fileName = `total_summary_${minDate}_to_${maxDate}.xlsx`;
                    XLSX.writeFile(workbook, fileName);
                });

                totalSummaryDisplay.appendChild(downloadButton);
                contentDisplay.appendChild(totalSummaryDisplay);

            } catch (error) {
                console.error("Error calculating total summary:", error);
                alert("An error occurred while generating the report.");
            }
        });
   }

    async function fetchTotalSummary() {
        try {
            const response = await fetch("/get_total_summary_data", { method: "GET" });
            const data = await response.json();

            if (data.error) {
                alert(data.error);
                return;
            }

            // Extract the min and max dates for the cumulative data
            const minDate = data.cumulative_metrics.min_date;
            const maxDate = data.cumulative_metrics.max_date;

            contentDisplay.innerHTML = `
                <h3 class='text-center'>Summary Report</h3>
                <table class='table table-bordered'>
                    <thead class='table-light'>
                        <tr>
                            <th style="width: 20%;">Metrics</th>
                            <th style="width: 30%;">Latest Values (${maxDate})</th>
                            <th style="width: 50%;">Cumulative Values (${minDate} ~ ${maxDate})</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td>Total Players</td><td>${data.latest_date_metrics.total_players}</td><td>${data.cumulative_metrics.total_players}</td></tr>
                        <tr><td>Total Bet</td><td>${data.latest_date_metrics.total_bet}</td><td>${data.cumulative_metrics.total_bet}</td></tr>
                        <tr><td>Total Win</td><td>${data.latest_date_metrics.total_win}</td><td>${data.cumulative_metrics.total_win}</td></tr>
                        <tr><td>Total Spins</td><td>${data.latest_date_metrics.total_spins}</td><td>${data.cumulative_metrics.total_spins}</td></tr>
                        <tr><td>Social Spins</td><td>${data.latest_date_metrics.social_spins}</td><td>${data.cumulative_metrics.social_spins}</td></tr>
                        <tr><td>Real Spins</td><td>${data.latest_date_metrics.reel_spins}</td><td>${data.cumulative_metrics.reel_spins}</td></tr>
                        <tr><td>RTP (%)</td><td>${data.latest_date_metrics.rtp}%</td><td>${data.cumulative_metrics.rtp}%</td></tr>
                        <tr><td>GGR (EUR)</td><td>${data.latest_date_metrics.ggr_eur}</td><td>${data.cumulative_metrics.ggr_eur}</td></tr>
                        <tr><td>GGR (GBP)</td><td>${data.latest_date_metrics.ggr_gbp}</td><td>${data.cumulative_metrics.ggr_gbp}</td></tr>
                    </tbody>
                </table>
            `;
        } catch (error) {
            console.error("Error fetching total summary:", error);
            alert("An error occurred while fetching the total summary.");
        }
    }

});
