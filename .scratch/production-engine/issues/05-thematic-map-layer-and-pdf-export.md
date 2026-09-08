# 05: Thematic AOI Map Visualization and Print-Styled PDF Report Export

**What to build:** Enhance the frontend to visually update the drawn Area of Interest polygon with a thematic fill color matching the dominant land cover class, display an amber warning badge when scene cloud cover exceeds 30%, and implement a dedicated print layout enabling users to export high-resolution, branded PDF reports directly via the browser print system.

**Blocked by:** 04: Hybrid Geological Intelligence with Regional Context and Dynamic Rule Fallback

**Status:** ready-for-agent

- [ ] Update the drawn Leaflet polygon styling upon analysis completion with a fill color corresponding to the dominant land cover class.
- [ ] Display an advisory Cloud Warning badge in the dashboard header when the API returns `cloud_warning: true`.
- [ ] Render all satellite provenance metadata (Scene ID, capture date, cloud cover, and mean NDVI) cleanly in the info card.
- [ ] Provide a dedicated print stylesheet (`@media print`) formatting the dashboard into a professional, multi-section briefing document.
- [ ] Wire the "Download PDF Report" button to trigger the browser print dialog with the print-optimized briefing layout.
