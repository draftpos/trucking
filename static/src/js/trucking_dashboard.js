/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, useState, useRef, onPatched } from "@odoo/owl";

function loadScript(url) {
    return new Promise((resolve, reject) => {
        if (document.querySelector(`script[src="${url}"]`)) {
            return resolve();
        }
        const script = document.createElement("script");
        script.src = url;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}


export class TruckingDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.lineChartRef = useRef("lineChart");
        this.donutChartRef = useRef("donutChart");
        this.charts = {};

        this.state = useState({
            dateFilter: 'all',
            metrics: {
                total_delivered: 0,
                in_progress: 0,
                total_invoices: 0,
                overdue_loads: 0,
                gross_profit: 0.0,
                total_load_value: 0.0,
                delivered_on_time: 0,
                delayed_deliveries: 0,
            },
            overdue_list: [],
            approvals_list: [],
            monthly_data: { labels: [], profit: [], revenue: [] },
            status_breakdown: { labels: [], data: [] },
            live_feed: [],
            upcoming_deliveries: [],
            calendarIndex: 0,
            calendarDelivery: null,
            calendarDays: [],
            calendarMonthYear: "",
            showPendingModal: false,
        });

        onWillStart(async () => {
            await loadScript("https://cdn.jsdelivr.net/npm/chart.js");
            await this.fetchData();
        });

        onMounted(() => {
            this.renderCharts();
        });
    }

    async fetchData() {
        const result = await this.orm.call("trucking.load", "get_dashboard_data", [this.state.dateFilter]);
        if (result) {
            Object.assign(this.state, result);
            this.state.calendarIndex = 0;
            this.updateCalendar();
            setTimeout(() => this.renderCharts(), 0);
        }
    }

    updateCalendar() {
        if (!this.state.upcoming_deliveries || this.state.upcoming_deliveries.length === 0) {
            this.state.calendarDelivery = null;
            return;
        }
        const delivery = this.state.upcoming_deliveries[this.state.calendarIndex];
        this.state.calendarDelivery = delivery;
        const dateParts = delivery.date.split('-'); // YYYY-MM-DD
        const year = parseInt(dateParts[0]);
        const month = parseInt(dateParts[1]) - 1; // 0-indexed
        const day = parseInt(dateParts[2]);

        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        
        let days = [];
        for (let i = 0; i < firstDay; i++) {
            days.push({ empty: true, id: 'e' + i });
        }
        for (let i = 1; i <= daysInMonth; i++) {
            days.push({ 
                day: i, 
                isDelivery: i === day,
                id: 'd' + i
            });
        }
        this.state.calendarDays = days;
        const monthName = new Date(year, month, 1).toLocaleString('default', { month: 'long' });
        this.state.calendarMonthYear = `${monthName} ${year}`;
    }

    nextDelivery() {
        if (this.state.calendarIndex < this.state.upcoming_deliveries.length - 1) {
            this.state.calendarIndex++;
            this.updateCalendar();
        }
    }

    prevDelivery() {
        if (this.state.calendarIndex > 0) {
            this.state.calendarIndex--;
            this.updateCalendar();
        }
    }

    async onDateFilterChange(ev) {
        this.state.dateFilter = ev.target.value;
        await this.fetchData();
    }

    togglePendingModal() {
        this.state.showPendingModal = !this.state.showPendingModal;
    }

    renderCharts() {
        if (this.charts.lineChart) {
            this.charts.lineChart.destroy();
        }
        if (this.charts.donutChart) {
            this.charts.donutChart.destroy();
        }

        if (this.lineChartRef.el) {
            const ctxLine = this.lineChartRef.el.getContext('2d');
            this.charts.lineChart = new Chart(ctxLine, {
                type: 'line',
                data: {
                    labels: this.state.monthly_data.labels,
                    datasets: [
                        {
                            label: 'Gross Profit',
                            data: this.state.monthly_data.profit,
                            borderColor: '#1bb786',
                            backgroundColor: 'rgba(27, 183, 134, 0.1)',
                            fill: true,
                            tension: 0.4
                        },
                        {
                            label: 'Revenue',
                            data: this.state.monthly_data.revenue,
                            borderColor: '#0d6efd',
                            backgroundColor: 'rgba(13, 110, 253, 0.1)',
                            fill: true,
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { 
                        legend: { 
                            position: 'bottom',
                            labels: {
                                color: '#2b3674',
                                font: { weight: 'bold', size: 12 }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    let label = context.dataset.label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    if (context.parsed.y !== null) {
                                        label += new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(context.parsed.y);
                                    }
                                    return label;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: {
                                color: '#2b3674',
                                font: { weight: 'bold' }
                            }
                        },
                        y: {
                            ticks: {
                                color: '#2b3674',
                                font: { weight: 'bold' },
                                callback: function(value, index, values) {
                                    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(value);
                                }
                            }
                        }
                    }
                }
            });
        }

        if (this.donutChartRef.el) {
            const ctxDonut = this.donutChartRef.el.getContext('2d');
            const bgColors = ['#0d6efd', '#20c997', '#f6a624', '#dc3545', '#7258fa', '#6c757d', '#17a2b8'];
            this.charts.donutChart = new Chart(ctxDonut, {
                type: 'doughnut',
                data: {
                    labels: this.state.status_breakdown.labels.map((label, index) => `${label} (${this.state.status_breakdown.data[index]})`),
                    datasets: [{
                        data: this.state.status_breakdown.data,
                        backgroundColor: bgColors.slice(0, this.state.status_breakdown.labels.length),
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { 
                        legend: { 
                            position: 'right',
                            labels: {
                                color: '#2b3674',
                                font: { weight: 'bold', size: 12 }
                            }
                        } 
                    },
                    cutout: '50%'
                }
            });
        }
    }

    openLoads(domain, title) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: title,
            res_model: "trucking.load",
            views: [[false, "list"], [false, "form"]],
            domain: domain,
        });
    }

    openLoadForm(loadId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "trucking.load",
            res_id: loadId,
            views: [[false, "form"]],
        }, {
            onClose: () => {
                this.fetchData();
            }
        });
    }
}

TruckingDashboard.template = "trucking.TruckingDashboard";

registry.category("actions").add("trucking_dashboard_action", TruckingDashboard);
