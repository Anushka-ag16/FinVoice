"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

const data = [
  { name: 'Equity', value: 300000, color: '#3B82F6' },
  { name: 'Debt', value: 87000, color: '#10B981' },
  { name: 'Gold', value: 58000, color: '#FBBF24' },
  { name: 'Cash', value: 38200, color: '#64748B' },
];

export function PortfolioDonut() {
  return (
    <div className="relative h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={80}
            outerRadius={100}
            paddingAngle={2}
            dataKey="value"
            stroke="none"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip 
            contentStyle={{ backgroundColor: '#1A2235', borderColor: '#3B82F6', borderRadius: '12px', color: '#F1F5F9' }}
            itemStyle={{ color: '#F1F5F9' }}
            formatter={(value: any) => [`₹${Number(value).toLocaleString('en-IN')}`, 'Value']}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <span className="text-sm text-slate-500">Total Assets</span>
        <span className="text-2xl font-bold text-slate-900">₹4.83L</span>
      </div>
      
      <div className="flex flex-wrap justify-center gap-4 mt-6">
        {data.map((item) => (
          <div key={item.name} className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
            <span className="text-sm text-slate-500">{item.name}</span>
            <span className="text-sm font-medium text-slate-700">{Math.round((item.value / 483200) * 100)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
