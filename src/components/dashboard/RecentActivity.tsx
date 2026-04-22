import { ActivityItem } from "@/types";
import Card from "@/components/shared/Card";
import { formatRelativeTime } from "@/lib/utils";

interface RecentActivityProps {
  activities: ActivityItem[];
}

export default function RecentActivity({ activities }: RecentActivityProps) {
  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-900">Recent Activity</h3>
        <span className="text-xs text-slate-400">Live feed</span>
      </div>
      <div className="space-y-3">
        {activities.map((activity) => (
          <div
            key={activity.id}
            className="flex items-start gap-3 p-3 rounded-xl bg-slate-50 hover:bg-slate-100 transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-xs font-medium text-slate-600 shrink-0 mt-0.5">
              {activity.user
                .split(" ")
                .map((n) => n[0])
                .join("")}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-slate-700 truncate">
                {activity.projectName}
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                {activity.action}
              </div>
            </div>
            <div className="text-xs text-slate-400 whitespace-nowrap shrink-0">
              {formatRelativeTime(activity.timestamp)}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
