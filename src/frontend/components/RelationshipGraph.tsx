import React, { useEffect, useState, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

interface Node {
  id: string;
  group: string;
}

interface Link {
  source: string;
  target: string;
  type: string;
}

interface GraphData {
  nodes: Node[];
  links: Link[];
}

const RelationshipGraph: React.FC = () => {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const graphRef = useRef<any>();

  useEffect(() => {
    fetch('http://localhost:8000/api/v1/graph/data')
      .then(res => res.json())
      .then(res => {
        if (res.status) {
          setData(res.data);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load graph data:", err);
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="p-10 text-center">Loading Relationship Graph...</div>;
  if (!data) return <div className="p-10 text-center">No relationship data available.</div>;

  return (
    <div className="w-full h-[600px] bg-slate-900 rounded-xl overflow-hidden border border-slate-700 relative">
      <div className="absolute top-4 left-4 z-10 bg-slate-800/80 p-3 rounded-lg border border-slate-600 text-xs">
        <h3 className="font-bold mb-2">Unified Relationship Graph</h3>
        <div className="flex items-center gap-2 mb-1">
          <span className="w-3 h-3 rounded-full bg-blue-500"></span>
          <span>Person</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-amber-500"></span>
          <span>Business</span>
        </div>
      </div>
      
      <ForceGraph2D
        ref={graphRef}
        graphData={data}
        nodeLabel="id"
        nodeAutoColorBy="group"
        linkDirectionalParticles={2}
        linkDirectionalParticleSpeed={d => 0.01}
        nodeCanvasObject={(node: any, ctx, globalScale) => {
          const label = node.id;
          const fontSize = 12/globalScale;
          ctx.font = `${fontSize}px Sans-Serif`;
          const textWidth = ctx.measureText(label).width;
          const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2); // some padding

          ctx.fillStyle = node.group === 'BUSINESS' ? '#f59e0b' : '#3b82f6';
          ctx.beginPath(); 
          ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI, false); 
          ctx.fill();

          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = '#cbd5e1';
          ctx.fillText(label, node.x, node.y + 10);
        }}
      />
    </div>
  );
};

export default RelationshipGraph;
