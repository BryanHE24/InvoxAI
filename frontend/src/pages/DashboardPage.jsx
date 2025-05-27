import React, { useState, useEffect } from 'react';
import analyticsService from '../services/analyticsService';
import { Bar, Line, Pie } from 'react-chartjs-2';
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend,
  PointElement, LineElement, ArcElement, Filler
} from 'chart.js';
import './DashboardPage.css';

ChartJS.register( CategoryScale, LinearScale, BarElement, PointElement, LineElement, ArcElement, Title, Tooltip, Legend, Filler );

const DashboardPage = () => {
  const [summary, setSummary] = useState({ total_spent: 0, total_invoices: 0 });
  const [vendorChartData, setVendorChartData] = useState(null);
  const [categoryChartData, setCategoryChartData] = useState(null);
  const [monthlyChartData, setMonthlyChartData] = useState(null);
  const [aiSummary, setAiSummary] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessages, setErrorMessages] = useState({
    summary: null, vendor: null, category: null, monthly: null, ai: null
  });

  let chartTextColor = '#65708f';
  let chartTitleColor = '#2c3e50';
  let chartGridColor = '#e2e8f0';

  useEffect(() => {
    if (typeof window !== "undefined" && typeof getComputedStyle !== "undefined") {
        const rootStyles = getComputedStyle(document.documentElement);
        chartTextColor = rootStyles.getPropertyValue('--text-secondary').trim() || chartTextColor;
        chartTitleColor = rootStyles.getPropertyValue('--text-primary').trim() || chartTitleColor;
        chartGridColor = rootStyles.getPropertyValue('--border-color').trim() || chartGridColor;
    }
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setErrorMessages({ summary: null, vendor: null, category: null, monthly: null, ai: null });
      console.log("DashboardPage: Initiating data fetch...");

      const results = await Promise.allSettled([
        analyticsService.getSummary(),
        analyticsService.getExpensesByVendor(5),
        analyticsService.getExpensesByCategory(5),
        analyticsService.getMonthlySpend(),
        analyticsService.getOpenAIDashboardSummary(),
      ]);

      console.log("DashboardPage: Promise.allSettled results:", JSON.parse(JSON.stringify(results)));
      const [summaryRes, vendorRes, categoryRes, monthlyRes, aiSummaryRes] = results;

      // Process Summary
      if (summaryRes.status === 'fulfilled' && summaryRes.value) {
        setSummary(summaryRes.value);
      } else {
        const e = summaryRes.reason;
        console.error("Error fetching summary:", e);
        setErrorMessages(prev => ({...prev, summary: e?.error || e?.message || "Failed summary."}));
      }

      // Process AI Summary
      if (aiSummaryRes.status === 'fulfilled') {
        if (aiSummaryRes.value && typeof aiSummaryRes.value.ai_insight_summary === 'string') {
          setAiSummary(aiSummaryRes.value.ai_insight_summary);
          setErrorMessages(prev => ({...prev, ai: null})); // Clear previous AI error
        } else if (aiSummaryRes.value && aiSummaryRes.value.error) {
          console.warn("AI Summary fulfilled but backend payload indicates error:", aiSummaryRes.value);
          setAiSummary('');
          setErrorMessages(prev => ({...prev, ai: aiSummaryRes.value.error + (aiSummaryRes.value.details ? ` (${aiSummaryRes.value.details})` : '')}));
        } else {
          console.warn("AI Summary fulfilled but data malformed or missing 'ai_insight_summary':", aiSummaryRes.value);
          setAiSummary('');
          setErrorMessages(prev => ({...prev, ai: "AI insights response structure was unexpected."}));
        }
      } else { // 'rejected'
        const e = aiSummaryRes.reason;
        console.error("AI Summary fetch promise rejected:", e);
        setAiSummary('');
        setErrorMessages(prev => ({...prev, ai: e?.error || e?.message || "Failed to fetch AI insights (request rejected)."}));
      }

      // Process Vendor Data
      if (vendorRes.status === 'fulfilled' && vendorRes.value && vendorRes.value.length > 0) {
        console.log("Fetched Vendor Data for chart:", vendorRes.value);
        setVendorChartData({
          labels: vendorRes.value.map(v => v.vendor_name || "N/A"),
          datasets: [{
            label: 'Spend by Vendor',
            data: vendorRes.value.map(v => v.total_spent_for_vendor || 0),
            backgroundColor: 'rgba(54, 162, 235, 0.8)',
            borderColor: 'rgba(54, 162, 235, 1)',
            borderWidth: 1,
            borderRadius: 8,
            borderSkipped: false,
          }],
        });
      } else {
        setVendorChartData(null);
        if (vendorRes.status === 'rejected'){
          const e=vendorRes.reason;
          setErrorMessages(prev => ({...prev, vendor: e?.error||e?.message||"Vendor data failed."}));
        } else if (vendorRes.status === 'fulfilled') {
          console.log("Vendor data is empty.");
        }
      }

      // Process Category Data
      if (categoryRes.status === 'fulfilled' && categoryRes.value && categoryRes.value.length > 0) {
        console.log("Fetched Category Data for chart:", categoryRes.value);
        setCategoryChartData({
          labels: categoryRes.value.map(c => c.user_category || 'Uncategorized'),
          datasets: [{
            label: 'Spend by Category',
            data: categoryRes.value.map(c => c.total_spent_for_category || 0),
            backgroundColor: [
              'rgba(54, 162, 235, 0.8)',
              'rgba(255, 99, 132, 0.8)',
              'rgba(255, 205, 86, 0.8)',
              'rgba(75, 192, 192, 0.8)',
              'rgba(153, 102, 255, 0.8)',
              'rgba(255, 159, 64, 0.8)',
              'rgba(199, 199, 199, 0.8)',
            ],
            borderColor: [
              'rgba(54, 162, 235, 1)',
              'rgba(255, 99, 132, 1)',
              'rgba(255, 205, 86, 1)',
              'rgba(75, 192, 192, 1)',
              'rgba(153, 102, 255, 1)',
              'rgba(255, 159, 64, 1)',
              'rgba(199, 199, 199, 1)',
            ],
            borderWidth: 2,
          }],
        });
      } else {
        setCategoryChartData(null);
        if (categoryRes.status === 'rejected'){
          const e=categoryRes.reason;
          setErrorMessages(prev => ({...prev, category: e?.error||e?.message||"Category data failed."}));
        } else if (categoryRes.status === 'fulfilled') {
          console.log("Category data is empty.");
        }
      }

      // Process Monthly Data
      if (monthlyRes.status === 'fulfilled' && monthlyRes.value && monthlyRes.value.length > 0) {
        console.log("Fetched Monthly Data for chart:", monthlyRes.value);
        setMonthlyChartData({
          labels: monthlyRes.value.map(m => m.month_year || "N/A"),
          datasets: [{
            label: 'Monthly Spend',
            data: monthlyRes.value.map(m => m.monthly_total || 0),
            fill: true,
            backgroundColor: 'rgba(54, 162, 235, 0.1)',
            borderColor: 'rgba(54, 162, 235, 1)',
            tension: 0.4,
            pointBackgroundColor: 'rgba(54, 162, 235, 1)',
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: 'rgba(54, 162, 235, 1)',
            pointRadius: 4
          }],
        });
      } else {
        setMonthlyChartData(null);
        if (monthlyRes.status === 'rejected'){
          const e=monthlyRes.reason;
          setErrorMessages(prev => ({...prev, monthly: e?.error||e?.message||"Monthly data failed."}));
        } else if (monthlyRes.status === 'fulfilled') {
          console.log("Monthly data is empty.");
        }
      }

      setIsLoading(false);
    };
    fetchData();
  }, []);

  // Chart Options
  const baseChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false, // Default, Pie chart will override
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: '#fff',
        bodyColor: '#fff',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1,
        cornerRadius: 6,
        displayColors: false,
        callbacks: {
          label: function(context) {
            return `$${context.parsed.y.toFixed(2)}`;
          }
        }
      }
    },
    scales: { // Only for Bar and Line
      y: {
        beginAtZero: true,
        grid: {
          color: chartGridColor,
          drawBorder: false,
        },
        ticks: {
          color: chartTextColor,
          callback: function(value) {
            return '$' + value.toFixed(0);
          }
        }
      },
      x: {
        grid: {
          display: false,
        },
        ticks: {
          color: chartTextColor,
          maxRotation: 45 // Applied for bar, can be overridden for line if needed
        }
      }
    }
  };

  const barChartOptions = {
    ...baseChartOptions
  };

  const lineChartOptions = {
    ...baseChartOptions,
    scales: { // Override x-axis ticks for line chart if needed
      ...baseChartOptions.scales,
      x: {
        ...baseChartOptions.scales.x,
        ticks: {
          color: chartTextColor,
          // maxRotation: 0, // Example: if you want no rotation for line chart x-axis labels
        }
      }
    },
    elements: {
      point: {
        hoverRadius: 8,
      }
    }
  };

  const pieChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          color: chartTextColor,
          padding: 20,
          usePointStyle: true,
          font: {
            size: 12
          }
        }
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: '#fff',
        bodyColor: '#fff',
        borderColor: 'rgba(54, 162, 235, 1)', // Can be dynamic based on slice color
        borderWidth: 1,
        cornerRadius: 6,
        callbacks: {
          label: function(context) {
            const label = context.label || '';
            const value = context.parsed || 0;
            const total = context.dataset.data.reduce((a, b) => a + b, 0);
            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
            return `${label}: $${value.toFixed(2)} (${percentage}%)`;
          }
        }
      }
    }
  };


  if (isLoading) return <div className="dashboard-loading card-invo">Loading Dashboard Data...</div>;
  const overallChartError = errorMessages.summary || errorMessages.vendor || errorMessages.category || errorMessages.monthly;

  return (
    <div className="dashboard-page-invo">
      <div className="page-header-invo"><h1>Dashboard</h1></div>
      {overallChartError && !isLoading && (
        <div className="dashboard-error-summary card-invo">
          <h4>Chart Data Loading Issues:</h4>
          <p>{overallChartError}</p>
        </div>
      )}

      <div className="summary-cards-grid-invo">
        <div className="stat-card-invo">
          <h3 className="card-title-invo">Total Processed Invoices</h3>
          <p className="card-value-invo">{summary.total_invoices || 0}</p>
        </div>
        <div className="stat-card-invo">
          <h3 className="card-title-invo">Total Processed Spend</h3>
          <p className="card-value-invo">${summary.total_spent ? summary.total_spent.toFixed(2) : '0.00'}</p>
        </div>
        <div className="stat-card-invo">
          <h3 className="card-title-invo">Avg. Invoice Amount</h3>
          <p className="card-value-invo">${summary.total_invoices > 0 ? (summary.total_spent / summary.total_invoices).toFixed(2) : '0.00'}</p>
        </div>
      </div>

      <div className="ai-insight-panel-invo">
        <h3 className="panel-title-invo">💡 AI Generated Insights</h3>
        {isLoading && !aiSummary && !errorMessages.ai && <p className="no-data-invo">Loading AI insights...</p>}
        {errorMessages.ai && <p className="error-message-invo">{errorMessages.ai}</p>}
        {aiSummary && !errorMessages.ai && (
          <p className="ai-summary-text-invo">
            {aiSummary.split('\n').map((line, i) => <span key={i}>{line}<br/></span>)}
          </p>
        )}
        {!aiSummary && !errorMessages.ai && !isLoading && <p className="no-data-invo">No AI insights available at the moment.</p>}
      </div>

      <div className="charts-grid-invo">
        <div className="chart-panel-invo">
          <h3 className="panel-title-invo">Top Vendors by Spend</h3>
          {vendorChartData ? (
            <div className="chart-container">
              <Bar options={barChartOptions} data={vendorChartData} />
            </div>
          ) : (
            <p className="no-data-invo">{errorMessages.vendor || 'No vendor data to display.'}</p>
          )}
        </div>

        <div className="chart-panel-invo">
          <h3 className="panel-title-invo">Spend by Category</h3>
          {categoryChartData ? (
            <div className="chart-container">
              <Pie options={pieChartOptions} data={categoryChartData} />
            </div>
          ) : (
            <p className="no-data-invo">{errorMessages.category || 'No category data. (Assign categories to invoices)'}</p>
          )}
        </div>

        <div className="chart-panel-invo line-chart-container-invo">
          <h3 className="panel-title-invo">Monthly Spending Trend</h3>
          {monthlyChartData ? (
            <div className="chart-container">
              <Line options={lineChartOptions} data={monthlyChartData} />
            </div>
          ) : (
            <p className="no-data-invo">{errorMessages.monthly || 'No monthly spending data.'}</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;