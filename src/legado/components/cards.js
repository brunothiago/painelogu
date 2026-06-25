function createNode(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== null && text !== undefined) node.textContent = text;
  return node;
}

export function metricGrid(metrics) {
  const grid = createNode("div", "metrics-grid");
  for (const metric of metrics) grid.append(metricCard(metric));
  return grid;
}

function metricCard({label, value, detail, tone = "default", delta, topRight}) {
  const card = createNode("article", `metric-card tone-${tone}`);
  const header = createNode("div", "metric-card__header");
  const labelNode = createNode("p", "metric-label", label);
  header.append(labelNode);
  if (topRight) header.append(createNode("span", "metric-top-right", topRight));
  const valueRow = createNode("div", "metric-value-row");
  const valueNode = createNode("strong", "metric-value", value);
  valueRow.append(valueNode);
  if (delta && delta.label) {
    const deltaTone = delta.tone || "neutral";
    const deltaNode = createNode("span", `metric-delta metric-delta--${deltaTone}`, delta.label);
    if (delta.title) {
      deltaNode.dataset.tooltip = delta.title;
      deltaNode.classList.add("has-tooltip");
    }
    valueRow.append(deltaNode);
  }
  card.append(header, valueRow);
  if (detail) card.append(createNode("p", "metric-detail", detail));
  return card;
}
