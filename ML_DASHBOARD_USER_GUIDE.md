# ML Dashboard User Guide 🤖

**Quick Start Guide for GitRate ML Analytics Dashboard**

---

## 🎯 Overview

The ML Analytics Dashboard provides AI-powered insights for repository analysis through interactive visualizations. Access powerful machine learning features without needing technical expertise.

---

## 🚀 Getting Started

### Access the Dashboard

1. **Start the Application:**
   ```bash
   uvicorn app:app --reload
   ```

2. **Open in Browser:**
   - Navigate to: `http://localhost:8000/`
   - Click the **"🤖 ML Analytics"** button in the header

3. **Alternative Direct Access:**
   - Go directly to: `http://localhost:8000/ml-dashboard`

---

## 📊 Dashboard Features

### 6 Interactive Tabs

The dashboard is organized into 6 feature tabs, each providing unique insights:

---

## 1. 🔍 Anomaly Detection

**Purpose:** Identify unusual patterns or deviations in repository metrics.

### What You'll See:

- **Status Indicator:** 
  - ⚠️ **Anomaly Detected** (Red) - Unusual activity found
  - ✅ **Normal** (Green) - No anomalies detected

- **Anomaly Score:** Percentage showing severity (0-100%)
- **Severity Level:** Critical / High / Medium / Low
- **Bar Chart:** Visual comparison of expected vs actual values

### How to Interpret:

**🔴 Critical (90-100%):**
- Immediate action required
- Significant deviation from normal patterns
- May indicate security issues or major problems

**🟠 High (70-89%):**
- Requires attention soon
- Notable deviation detected
- Investigate underlying causes

**🟡 Medium (40-69%):**
- Monitor the situation
- Moderate deviation observed
- May be expected variation

**🟢 Low (0-39%):**
- No action needed
- Within normal range
- Regular fluctuation

### Example Use Cases:

- Detect sudden spike in commit failures
- Identify unusual code quality degradation
- Spot irregular contributor activity
- Find unexpected security vulnerabilities

---

## 2. 📈 Score Predictions

**Purpose:** Forecast future repository quality scores based on historical trends.

### What You'll See:

- **Predicted Score:** Future quality score (0-100)
- **Trend Indicator:** 
  - 📈 Improving
  - 📉 Declining
  - ➡️ Stable
- **Confidence Level:** How certain the prediction is (%)
- **Prediction Range:** Min/Max possible scores
- **Line Chart:** Historical + Predicted scores

### How to Interpret:

**Chart Elements:**
- **Solid Blue Line:** Historical scores (last 7 days)
- **Dashed Green Line:** Predicted scores (next 7 days)

**Confidence Levels:**
- **90-100%:** Very high confidence
- **70-89%:** High confidence
- **50-69%:** Moderate confidence
- **Below 50%:** Low confidence (more uncertainty)

### Example Use Cases:

- Plan resource allocation for upcoming sprints
- Predict if quality will meet release criteria
- Identify when intervention might be needed
- Forecast team performance trends

### Actionable Insights:

**If score is predicted to decline:**
- Increase code review rigor
- Schedule refactoring sessions
- Add more automated tests
- Improve documentation

**If score is predicted to improve:**
- Maintain current practices
- Document what's working well
- Share best practices with team

---

## 3. 💡 Insights

**Purpose:** Get AI-generated recommendations and actionable insights.

### What You'll See:

**Insight Cards** containing:
- **Title:** Brief description of the insight
- **Severity Badge:** Critical / High / Medium / Low
- **Description:** Detailed explanation
- **Evidence:** Data supporting the insight
- **Recommendations:** 3-5 actionable steps

### Severity Color Coding:

- **🔴 Critical (Red):** Urgent issues requiring immediate action
- **🟠 High (Orange):** Important items needing attention soon
- **🟡 Medium (Yellow):** Moderate priority improvements
- **🟢 Low (Green):** Nice-to-have enhancements

### Types of Insights:

1. **Security Insights:**
   - Vulnerability detection
   - Dependency risks
   - Authentication issues

2. **Code Quality Insights:**
   - Code smell detection
   - Complexity analysis
   - Technical debt assessment

3. **Team Performance Insights:**
   - Collaboration patterns
   - Review effectiveness
   - Contributor activity

4. **Documentation Insights:**
   - Missing documentation
   - Outdated README files
   - Incomplete API docs

5. **Testing Insights:**
   - Test coverage gaps
   - Flaky tests
   - Missing test types

### How to Use:

1. **Read Description:** Understand what the issue is
2. **Review Evidence:** See the data backing the insight
3. **Follow Recommendations:** Implement suggested actions
4. **Prioritize by Severity:** Start with Critical/High items

### Example Insight:

```
Title: High Code Complexity Detected
Severity: High 🟠
Description: Multiple functions exceed complexity threshold (cyclomatic complexity > 10)
Evidence: 
  - UserService.processOrder() - complexity: 18
  - ReportGenerator.createReport() - complexity: 15
Recommendations:
  1. Break down complex functions into smaller units
  2. Extract helper methods for repeated logic
  3. Apply Single Responsibility Principle
  4. Add unit tests for complex code paths
  5. Consider refactoring using design patterns
```

---

## 4. 🎯 Repository Clustering

**Purpose:** Group similar repositories based on characteristics and patterns.

### What You'll See:

**Cluster Cards** showing:
- **Cluster ID:** Unique identifier (e.g., Cluster 1, Cluster 2)
- **Description:** Common characteristics
- **Repository Count:** Number of repos in cluster
- **Repository Tags:** List of repositories in the cluster

### How Clustering Works:

Repositories are grouped by similarity in:
- Code quality metrics
- Team size and activity
- Technology stack
- Commit patterns
- Issue frequency

### Example Use Cases:

1. **Identify Best Practices:**
   - Find clusters with high-performing repos
   - Study what makes them successful
   - Apply patterns to other clusters

2. **Resource Allocation:**
   - Assign specialized teams to similar projects
   - Share expertise across cluster members
   - Optimize tooling for cluster characteristics

3. **Risk Management:**
   - Identify struggling repository clusters
   - Apply targeted interventions
   - Monitor cluster migration over time

### Example Cluster:

```
Cluster 1: High-Quality Enterprise Projects
Description: Well-maintained, highly tested, large teams
Repositories (5):
  - payment-service
  - user-management
  - api-gateway
  - auth-service
  - notification-engine
Characteristics:
  - Average Score: 92/100
  - Test Coverage: >85%
  - Team Size: 8-12 developers
  - Active Maintenance: Daily commits
```

---

## 5. 📊 Trend Forecasts

**Purpose:** Long-term quality trend predictions (90 days).

### What You'll See:

- **Forecast Chart:** 90-day quality score projection
- **Weekly Data Points:** Score predictions for each week
- **Trend Direction:** Overall trajectory (improving/declining/stable)
- **Confidence Visualization:** Uncertainty ranges

### How to Interpret:

**Chart Elements:**
- **Purple Line:** Forecasted scores
- **Shaded Area:** Confidence interval (potential range)
- **Data Points:** Weekly score predictions

**Trend Patterns:**

1. **📈 Upward Trend:**
   - Quality consistently improving
   - Current practices effective
   - Positive team momentum

2. **📉 Downward Trend:**
   - Quality deteriorating
   - Intervention needed
   - Review processes and practices

3. **➡️ Flat Trend:**
   - Stable quality
   - Consistent performance
   - Mature codebase

4. **📊 Volatile Trend:**
   - Fluctuating quality
   - Inconsistent practices
   - May need standardization

### Planning Applications:

**Short-term (1-4 weeks):**
- Sprint planning
- Feature prioritization
- Testing resource allocation

**Medium-term (1-2 months):**
- Release planning
- Refactoring initiatives
- Team training needs

**Long-term (3 months):**
- Strategic roadmap
- Architecture decisions
- Technical debt management

### Example Scenarios:

**Scenario 1: Upcoming Release**
- **Current Score:** 78
- **30-day Forecast:** 85 (improving)
- **Action:** Proceed with release, continue current practices

**Scenario 2: Quality Decline**
- **Current Score:** 82
- **60-day Forecast:** 72 (declining)
- **Action:** Schedule refactoring sprint, increase code reviews

---

## 6. ❤️ Health Status

**Purpose:** Overall repository health assessment and monitoring.

### What You'll See:

**Health Dashboard:**
- **Status Emoji:** 
  - ✅ Healthy (Green)
  - ⚠️ Warning (Yellow)
  - 🔴 Critical (Red)
- **Health Description:** Current state summary
- **Average Score:** Overall quality metric
- **Trend Indicator:** Recent direction (📈/📉/➡️)
- **Consistency Score:** How stable quality has been (%)
- **Total Audits:** Historical audit count
- **Last Audit Date:** Most recent analysis timestamp

### Health Status Levels:

**✅ Healthy (Score 80-100):**
- Repository is well-maintained
- Quality is consistently high
- No major issues detected
- Best practices being followed

**⚠️ Warning (Score 60-79):**
- Some concerns detected
- Quality fluctuating
- Improvement recommended
- Monitor closely

**🔴 Critical (Score 0-59):**
- Significant issues present
- Immediate action required
- Quality unacceptable
- Risk of project failure

### Consistency Metric:

Measures stability of quality over time:
- **90-100%:** Very consistent (reliable)
- **70-89%:** Moderately consistent (some variation)
- **50-69%:** Inconsistent (high variability)
- **Below 50%:** Very inconsistent (unstable)

### Example Use Cases:

1. **Executive Reporting:**
   - Quick health overview
   - Summarize repository status
   - Track improvement over time

2. **Team Standup:**
   - Discuss current health status
   - Address declining trends
   - Celebrate improvements

3. **Stakeholder Communication:**
   - Provide high-level metrics
   - Demonstrate quality commitment
   - Show investment returns

### Example Health Status:

```
Status: ✅ Healthy
Description: Repository is well-maintained with consistent quality
Average Score: 87/100
Trend: 📈 Improving
Consistency: 92% (Very Stable)
Total Audits: 156
Last Audit: 2024-01-15 14:30:00
```

---

## 🎨 Visual Elements

### Color Meanings

**Status Colors:**
- 🟢 **Green:** Good / Healthy / Normal
- 🟡 **Yellow:** Warning / Medium Priority
- 🟠 **Orange:** High Priority / Attention Needed
- 🔴 **Red:** Critical / Urgent / Anomaly

**Trend Indicators:**
- 📈 **Upward Arrow:** Improving / Increasing
- 📉 **Downward Arrow:** Declining / Decreasing
- ➡️ **Right Arrow:** Stable / No Change

### Chart Types

1. **Bar Charts:** Comparing discrete values (anomalies)
2. **Line Charts:** Showing trends over time (predictions, forecasts)
3. **Card Layouts:** Displaying structured information (insights, clusters)

---

## 🔄 Common Workflows

### Daily Check-in Workflow

1. **Navigate to ML Dashboard**
2. **Check Health Status Tab**
   - Review overall health
   - Note any warnings
3. **Review Insights Tab**
   - Read new insights
   - Prioritize actions
4. **Check Anomaly Detection**
   - Look for unusual patterns
   - Investigate anomalies

**Time Required:** 5-10 minutes

---

### Sprint Planning Workflow

1. **Open Trend Forecasts Tab**
   - Review 30-day forecast
   - Identify quality trends
2. **Check Score Predictions**
   - Estimate end-of-sprint quality
   - Plan capacity accordingly
3. **Review Insights**
   - Identify improvement opportunities
   - Add to sprint backlog
4. **Check Clustering**
   - Compare with similar projects
   - Learn from high-performers

**Time Required:** 15-20 minutes

---

### Quarterly Review Workflow

1. **Health Status Tab**
   - Overall health assessment
   - Consistency analysis
2. **Trend Forecasts Tab**
   - 90-day quality projection
   - Long-term trend identification
3. **Clustering Tab**
   - Portfolio comparison
   - Best practice identification
4. **Insights Tab**
   - Strategic improvement areas
   - Technical debt planning

**Time Required:** 30-45 minutes

---

## 💡 Tips & Best Practices

### 1. Regular Monitoring

- Check dashboard daily for anomalies
- Review insights weekly
- Analyze trends monthly

### 2. Act on Insights

- Don't just read – implement recommendations
- Prioritize by severity
- Track improvement over time

### 3. Compare Repositories

- Use clustering to identify patterns
- Learn from high-performing repos
- Share best practices across teams

### 4. Trend Analysis

- Watch for directional changes
- Investigate sudden shifts
- Plan proactively based on forecasts

### 5. Team Collaboration

- Share dashboard in standups
- Discuss insights as a team
- Assign action items from recommendations

---

## ❓ FAQ

**Q: How often is data updated?**
A: Data is fetched in real-time when you select a repository or switch tabs.

**Q: What do I do if I see a critical anomaly?**
A: 
1. Review the anomaly details
2. Check recent commits/changes
3. Investigate root cause
4. Address the underlying issue
5. Monitor for resolution

**Q: How accurate are the predictions?**
A: Accuracy depends on historical data availability. Check the confidence percentage – higher confidence means more reliable predictions.

**Q: Can I export the data?**
A: Currently, data export is not available. Future versions may include CSV/PDF export functionality.

**Q: What if a chart doesn't load?**
A: 
1. Check your internet connection (Chart.js loads from CDN)
2. Ensure the backend API is running
3. Try refreshing the page
4. Check browser console for errors

**Q: How do I switch between repositories?**
A: Use the repository selector dropdown at the top of the dashboard. Select a repository and data will load automatically.

**Q: What does "consistency" mean in health status?**
A: Consistency measures how stable your quality score has been over time. High consistency means predictable, reliable quality.

**Q: Can I customize the dashboard?**
A: Currently, the dashboard layout is fixed. Custom layouts may be added in future versions.

---

## 🛠️ Troubleshooting

### Dashboard Won't Load

**Symptoms:** Blank page or loading spinner stuck

**Solutions:**
1. Ensure app is running: `uvicorn app:app --reload`
2. Check URL is correct: `http://localhost:8000/ml-dashboard`
3. Clear browser cache
4. Try incognito/private browsing mode

---

### Charts Not Displaying

**Symptoms:** Empty chart areas or "Chart not available" message

**Solutions:**
1. Check internet connection (Chart.js CDN required)
2. Verify API endpoints are responding
3. Check browser console for JavaScript errors
4. Ensure repository has sufficient historical data

---

### No Data for Repository

**Symptoms:** "No data available" messages

**Solutions:**
1. Select a different repository from dropdown
2. Ensure repository has been audited previously
3. Use demo repositories: "test-repo" or "sample-project"
4. Check if ML models have processed the repository

---

### Navigation Link Not Working

**Symptoms:** Can't get to ML dashboard from main dashboard

**Solutions:**
1. Check if ML dashboard router is registered in app.py
2. Verify FastAPI app is running
3. Try direct URL: `http://localhost:8000/ml-dashboard`
4. Clear browser cache

---

## 📚 Related Resources

- **Phase 8 Completion Report:** [PHASE_8_COMPLETION.md](PHASE_8_COMPLETION.md)
- **ML Features Documentation:** [PHASE_7_COMPLETION.md](PHASE_7_COMPLETION.md)
- **API Documentation:** `http://localhost:8000/docs`
- **Project README:** [README.md](README.md)

---

## 🎓 Training Resources

### For New Users

1. **First-Time Setup:** Follow "Getting Started" section
2. **Feature Overview:** Watch demonstration of each tab
3. **Practice Workflow:** Complete "Daily Check-in Workflow"
4. **Ask Questions:** Refer to FAQ or contact support

### For Advanced Users

1. **API Integration:** Study `/api/ml/*` endpoints
2. **Custom Visualizations:** Explore Chart.js documentation
3. **Data Analysis:** Export and analyze trends
4. **Process Optimization:** Develop custom workflows

---

## 📞 Support

**For Technical Issues:**
- Check troubleshooting section first
- Review browser console errors
- Consult API documentation at `/docs`

**For Feature Requests:**
- Submit via project issue tracker
- Include detailed use case description
- Provide mockups if possible

---

## 🎉 Quick Start Checklist

- [ ] Start application: `uvicorn app:app --reload`
- [ ] Open browser to `http://localhost:8000/`
- [ ] Click "🤖 ML Analytics" button
- [ ] Select a repository from dropdown
- [ ] Explore each of the 6 tabs
- [ ] Read and understand insights
- [ ] Note any critical issues
- [ ] Implement recommendations
- [ ] Monitor improvements over time

---

**Happy Analyzing! 🚀**

*Last Updated: 2024*  
*Version: 1.0*  
*For GitRate ML Analytics Dashboard*
