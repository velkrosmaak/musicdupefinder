document.addEventListener('DOMContentLoaded', function() {
    // --- General Utility Functions ---
    const fetchData = async (url) => {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    };

    const createTooltip = () => {
        return d3.select("body").append("div")
            .attr("class", "tooltip")
            .style("opacity", 0);
    };

    const showTooltip = (tooltip, event, data, textFn) => {
        tooltip.html(textFn(data))
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 28) + "px")
            .transition()
            .duration(200)
            .style("opacity", .9);
    };

    const hideTooltip = (tooltip) => {
        tooltip.transition()
            .duration(500)
            .style("opacity", 0);
    };

    // --- Summary Dashboard ---
    const loadSummary = async () => {
        try {
            const data = await fetchData('/api/summary');
            document.getElementById('total-tracks').innerText = data.total_duplicate_tracks.toLocaleString();
            document.getElementById('total-groups').innerText = data.total_duplicate_groups.toLocaleString();
            document.getElementById('unique-artists').innerText = data.unique_artists.toLocaleString();
            document.getElementById('unique-albums').innerText = data.unique_albums.toLocaleString();
            document.getElementById('tracks-to-delete').innerText = data.tracks_to_delete_count.toLocaleString();

            // Create "Will Keep" vs "Won't Keep" pie chart
            createPieChart(
                '#will-keep-chart',
                data.will_keep_ratio,
                'Tracks to Keep vs. Discard',
                (d) => `${d[0]}: ${d[1].toLocaleString()} tracks`
            );

        } catch (error) {
            console.error('Error loading summary data:', error);
            document.getElementById('total-tracks').innerText = "Error";
            document.getElementById('total-groups').innerText = "Error";
            document.getElementById('unique-artists').innerText = "Error";
            document.getElementById('unique-albums').innerText = "Check CSV Path";
            document.getElementById('tracks-to-delete').innerText = "!";
        }
    };

    // --- Bar Chart Function (Reusable) ---
    const createBarChart = (selector, data, xLabel, yLabel, tooltipTextFn) => {
        const margin = { top: 20, right: 30, bottom: 70, left: 60 };
        const container = d3.select(selector);
        const containerWidth = container.node().getBoundingClientRect().width;
        const width = containerWidth - margin.left - margin.right;
        const height = 400 - margin.top - margin.bottom;

        container.html(''); // Clear previous chart
        const svg = container.append("svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`);

        const x = d3.scaleBand()
            .range([0, width])
            .padding(0.1);

        const y = d3.scaleLinear()
            .range([height, 0]);

        x.domain(Object.keys(data));
        y.domain([0, d3.max(Object.values(data))]);

        svg.append("g")
            .attr("transform", `translate(0,)`)
            .call(d3.axisBottom(x))
            .selectAll("text")
            .attr("transform", "translate(-10,0)rotate(-45)")
            .style("text-anchor", "end");

        svg.append("g")
            .call(d3.axisLeft(y));

        const tooltip = createTooltip();

        svg.selectAll(".bar")
            .data(Object.entries(data))
            .enter().append("rect")
            .attr("class", "bar")
            .attr("x", d => x(d[0]))
            .attr("width", x.bandwidth())
            .attr("y", d => y(d[1]))
            .attr("height", d => height - y(d[1]))
            .on("mouseover", function(event, d) {
                d3.select(this).style("fill", "orange");
                showTooltip(tooltip, event, d, tooltipTextFn);
            })
            .on("mouseout", function() {
                d3.select(this).style("fill", "steelblue");
                hideTooltip(tooltip);
            });

        // Add X axis label
        svg.append("text")
            .attr("text-anchor", "end")
            .attr("x", width / 2 + margin.left)
            .attr("y", height + margin.bottom - 10)
            .text(xLabel);

        // Add Y axis label
        svg.append("text")
            .attr("text-anchor", "end")
            .attr("transform", "rotate(-90)")
            .attr("y", -margin.left + 20)
            .attr("x", -height / 2)
            .text(yLabel);
    };

    // --- Quality Distribution Chart ---
    const loadQualityDistribution = async () => {
        try {
            const data = await fetchData('/api/duplicates_by_quality');
            createBarChart(
                '#quality-chart',
                data,
                'Quality (kbps)',
                'Number of Tracks',
                (d) => `Quality: ${d[0]} kbps<br>Tracks: ${d[1].toLocaleString()}`
            );
        } catch (error) {
            console.error('Error loading quality distribution:', error);
        }
    };

    // --- Pie Chart Function (Reusable) ---
    const createPieChart = (selector, data, title, tooltipTextFn) => {
        const width = 400;
        const height = 400;
        const radius = Math.min(width, height) / 2;

        const container = d3.select(selector);
        container.html(''); // Clear previous chart

        const svg = container.append("svg")
            .attr("width", width)
            .attr("height", height)
            .append("g")
            .attr("transform", `translate(${width / 2},${height / 2})`);

        const color = d3.scaleOrdinal(d3.schemeCategory10);

        const pie = d3.pie()
            .value(d => d[1])
            .sort(null);

        const arc = d3.arc()
            .innerRadius(0)
            .outerRadius(radius);

        const arcs = svg.selectAll(".arc")
            .data(pie(Object.entries(data)))
            .enter().append("g")
            .attr("class", "arc");

        const tooltip = createTooltip();

        arcs.append("path")
            .attr("d", arc)
            .attr("fill", d => color(d.data[0]))
            .on("mouseover", function(event, d) {
                d3.select(this).style("opacity", 0.8);
                showTooltip(tooltip, event, d.data, tooltipTextFn);
            })
            .on("mouseout", function() {
                d3.select(this).style("opacity", 1);
                hideTooltip(tooltip);
            });

        arcs.append("text")
            .attr("transform", d => `translate(${arc.centroid(d)})`)
            .attr("text-anchor", "middle")
            .text(d => `${d.data[0]} (${d.data[1].toLocaleString()})`)
            .style("font-size", "0.8em")
            .style("fill", "white");

        svg.append("text")
            .attr("text-anchor", "middle")
            .attr("y", -radius - 10)
            .text(title)
            .style("font-size", "1.2em")
            .style("fill", "#0056b3");
    };

    const loadFormatDistribution = async () => {
        try {
            const data = await fetchData('/api/duplicates_by_format');
            createPieChart(
                '#format-chart',
                data,
                'Duplicate Tracks by Format',
                (d) => `Format: ${d[0]}<br>Tracks: ${d[1].toLocaleString()}`
            );
        } catch (error) {
            console.error('Error loading format distribution:', error);
        }
    };

    const loadYearDistribution = async () => {
        try {
            const data = await fetchData('/api/duplicates_by_year');
            createBarChart(
                '#year-chart',
                data,
                'Year',
                'Number of Tracks',
                (d) => `Year: ${d[0]}<br>Tracks: ${d[1].toLocaleString()}`
            );
        } catch (error) {
            console.error('Error loading year distribution:', error);
        }
    };

    // --- Top Artists/Albums Duplicates Charts ---
    const loadTopArtistsDuplicates = async () => {
        try {
            const data = await fetchData('/api/top_artists_duplicates?top_n=10');
            createBarChart(
                '#artists-chart',
                data,
                'Artist',
                'Number of Duplicates',
                (d) => `Artist: ${d[0]}<br>Duplicates: ${d[1].toLocaleString()}`
            );
        } catch (error) {
            console.error('Error loading top artists duplicates:', error);
        }
    };

    const loadTopAlbumsDuplicates = async () => {
        try {
            const data = await fetchData('/api/top_albums_duplicates?top_n=10');
            createBarChart(
                '#albums-chart',
                data,
                'Album',
                'Number of Duplicates',
                (d) => `Album: ${d[0]}<br>Duplicates: ${d[1].toLocaleString()}`
            );
        } catch (error) {
            console.error('Error loading top albums duplicates:', error);
        }
    };

    // --- Duplicate Groups List and Modal ---
    let currentPage = 1;
    const perPage = 20;
    let totalFilteredGroups = 0; // Keep track of total filtered groups for pagination

    const loadDuplicateGroupsList = async (page = 1, searchTerm = '') => {
        try {
            const url = `/api/duplicate_groups?page=${page}&per_page=${perPage}&search=${encodeURIComponent(searchTerm)}`;
            const data = await fetchData(url);

            totalFilteredGroups = data.total_groups; // Update total filtered groups

            const tbody = d3.select('#groups-table tbody');
            tbody.html(''); // Clear existing rows

            data.groups.forEach(group => {
                const row = tbody.append('tr');
                row.append('td').text(group['Group ID']);
                row.append('td').text(group['total_tracks']);
                row.append('td').text(group['highest_quality_count']);
                row.append('td').text(group['will_keep_count']);
                row.append('td').text(group['artists']);
                row.append('td').text(group['albums']);
                row.append('td').append('button')
                    .text('View Details')
                    .on('click', () => showGroupDetailsModal(group['Group ID']));
            });

            document.getElementById('page-info').innerText = `Page ${page} of ${Math.ceil(totalFilteredGroups / perPage)}`;
            document.getElementById('prev-page').disabled = page === 1;
            document.getElementById('next-page').disabled = (page * perPage) >= totalFilteredGroups;
            currentPage = page;

        } catch (error) {
            console.error('Error loading duplicate groups:', error);
        }
    };

    const showGroupDetailsModal = async (groupId) => {
        try {
            const data = await fetchData(`/api/group_details/${groupId}`);
            const modal = document.getElementById('group-detail-modal');
            document.getElementById('modal-group-id').innerText = groupId;
            const tracksContainer = d3.select('#modal-group-tracks');
            tracksContainer.html(''); // Clear previous details

            if (data.length > 0) {
                const table = tracksContainer.append('table');
                const thead = table.append('thead');
                const tbody = table.append('tbody');

                // Define headers in desired order
                const orderedHeaders = [
                    'Quality (kbps)', 'Highest Quality', 'Will Keep', 'Format',
                    'Artist', 'Title', 'Album', 'Year', 'Path'
                ];

                thead.append('tr').selectAll('th')
                    .data(orderedHeaders)
                    .enter().append('th')
                    .text(d => d);

                // Populate table rows
                data.forEach(track => {
                    const row = tbody.append('tr');
                    row.selectAll('td')
                        .data(orderedHeaders.map(header => {
                            let value = track[header];
                            if (header === 'Highest Quality' || header === 'Will Keep') {
                                return value ? 'Yes' : 'No';
                            }
                            return value;
                        }))
                        .enter().append('td')
                        .html(function(d, i) {
                            // Highlight 'Highest Quality' and 'Will Keep' status
                            if (orderedHeaders[i] === 'Highest Quality' && d === 'Yes') {
                                return `<span style="color: green; font-weight: bold;">${d}</span>`;
                            }
                            if (orderedHeaders[i] === 'Will Keep' && d === 'No') {
                                return `<span style="color: red; font-weight: bold;">${d}</span>`;
                            }
                            return d;
                        });
                });
            } else {
                tracksContainer.text('No tracks found for this group.');
            }

            modal.style.display = 'block';
        } catch (error) {
            console.error(`Error loading details for group ${groupId}:`, error);
        }
    };

    const modal = document.getElementById('group-detail-modal');
    const closeButton = document.querySelector('.close-button');
    closeButton.onclick = () => {
        modal.style.display = 'none';
    };
    window.onclick = (event) => {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    };

    // Pagination controls
    document.getElementById('prev-page').addEventListener('click', () => {
        if (currentPage > 1) {
            loadDuplicateGroupsList(currentPage - 1, document.getElementById('group-search').value);
        }
    });

    document.getElementById('next-page').addEventListener('click', () => {
        const totalPages = Math.ceil(totalFilteredGroups / perPage);
        if (currentPage < totalPages) {
            loadDuplicateGroupsList(currentPage + 1, document.getElementById('group-search').value);
        }
    });

    // Search functionality with debounce
    let searchTimeout;
    document.getElementById('group-search').addEventListener('input', (event) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            loadDuplicateGroupsList(1, event.target.value);
        }, 300); // Debounce for 300ms
    });


    // --- Initialize Dashboard ---
    loadSummary();
    loadQualityDistribution();
    loadFormatDistribution();
    loadYearDistribution(); // Load year distribution
    loadTopArtistsDuplicates();
    loadTopAlbumsDuplicates();
    loadDuplicateGroupsList(); // Initial load of the first page
});
