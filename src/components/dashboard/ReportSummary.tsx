import { HealthReport } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, CheckCircle2, Info } from "lucide-react";

interface ReportSummaryProps {
  report: HealthReport | null;
}

export function ReportSummary({ report }: ReportSummaryProps) {
  if (!report) return null;

  const isGood = report.overallRating === "GOOD";
  const isFair = report.overallRating === "FAIR";

  return (
    <div className="space-y-6">
      <Card className="border-l-4 border-l-blue-500">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle>Health Score</CardTitle>
            <Badge variant={isGood ? "success" : isFair ? "warning" : "destructive"} className="text-sm px-3 py-1">
              {report.overallRating} ({report.healthScore}/100)
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700 mb-4">
            <div 
              className={`h-2.5 rounded-full ${isGood ? 'bg-green-500' : isFair ? 'bg-amber-500' : 'bg-red-500'}`} 
              style={{ width: `${report.healthScore}%` }}
            ></div>
          </div>
          
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-semibold mb-1 flex items-center">
                <Info className="w-4 h-4 mr-2 text-blue-500" />
                Narrative Report
              </h4>
              <p className="text-sm text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-900 p-3 rounded-md">
                {report.narrative}
              </p>
            </div>

            <div>
              <h4 className="text-sm font-semibold mb-1 flex items-center">
                <CheckCircle2 className="w-4 h-4 mr-2 text-green-500" />
                Formal Summary (Copy to report)
              </h4>
              <pre className="text-xs text-gray-800 dark:text-gray-200 bg-gray-100 dark:bg-gray-800 p-3 rounded-md whitespace-pre-wrap font-sans">
                {report.summary}
              </pre>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
