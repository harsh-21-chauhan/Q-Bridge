// Render a small, safe subset of text structure. Never interpret model HTML.
// Friendly labels are presentation only. Exact IDs remain in technical records.
export default function AssistantAnswer({ text, trace = [] }) {
  const labels = new Map();
  for (const step of trace) {
    const data = step.evidence;
    if (step.tool === 'compare_budget') {
      labels.set(data.previous.experiment_id, 'the original experiment');
      labels.set(data.current.experiment_id, 'the budget alternative');
    } else labels.set(data.experiment_id, 'the selected experiment');
  }
  const display = text.replace(
    /qb_[0-9a-f]{32}/g,
    (id) => labels.get(id) || 'the referenced experiment',
  );
  const blocks = [];
  let bullets = [];
  function flush() {
    if (bullets.length) {
      blocks.push(
        <ul key={blocks.length}>
          {bullets.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ul>,
      );
      bullets = [];
    }
  }
  for (const raw of display.split('\n')) {
    const line = raw.trim();
    if (!line) {
      flush();
      continue;
    }
    const heading = line
      .replace(/^#{1,3}\s+/, '')
      .replace(/\*\*/g, '')
      .match(/^(Decision|Conclusion|Evidence|Uncertainty|Limitations?)(?::\s*(.*)|\s*)$/i);
    if (heading) {
      flush();
      blocks.push(
        <div className="answer-section" key={blocks.length}>
          <h3>{heading[1]}</h3>
          {heading[2] && <p>{heading[2]}</p>}
        </div>,
      );
    } else if (/^[-*•]\s+/.test(line)) bullets.push(line.replace(/^[-*•]\s+/, ''));
    else {
      flush();
      blocks.push(<p key={blocks.length}>{line}</p>);
    }
  }
  flush();
  return <div className="assistant-answer">{blocks}</div>;
}
