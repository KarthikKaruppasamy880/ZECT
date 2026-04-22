import Header from "@/components/layout/Header";
import Card from "@/components/shared/Card";

const checklistItems = [
  { category: "Infrastructure", items: [
    { title: "AWS resources provisioned (ECS, RDS, ElastiCache, S3)", status: "pass" },
    { title: "DNS records configured for staging and production", status: "pass" },
    { title: "SSL certificates issued and auto-renewing", status: "pass" },
    { title: "CloudFront distribution configured with caching rules", status: "pass" },
    { title: "Auto-scaling policies configured for ECS tasks", status: "warning" },
  ]},
  { category: "Security", items: [
    { title: "Secrets stored in AWS Secrets Manager (no hardcoded values)", status: "pass" },
    { title: "IAM roles scoped to minimum required permissions", status: "pass" },
    { title: "WAF rules configured for API endpoints", status: "pass" },
    { title: "Penetration test completed with no critical findings", status: "pass" },
    { title: "Data encryption at rest (AES-256) and in transit (TLS 1.3)", status: "pass" },
  ]},
  { category: "Testing", items: [
    { title: "All unit tests passing (coverage: 82%)", status: "pass" },
    { title: "Integration tests passing against staging environment", status: "pass" },
    { title: "End-to-end tests passing for critical user flows", status: "warning" },
    { title: "Load test completed — 500 concurrent users sustained", status: "pass" },
    { title: "Disaster recovery procedure tested and documented", status: "fail" },
  ]},
  { category: "Operations", items: [
    { title: "Monitoring dashboards configured (CloudWatch, Datadog)", status: "pass" },
    { title: "Alert rules configured for error rates and latency", status: "pass" },
    { title: "Runbook documented for common operational scenarios", status: "pass" },
    { title: "Rollback procedure tested and documented", status: "pass" },
    { title: "On-call rotation assigned for first 2 weeks post-launch", status: "warning" },
  ]},
  { category: "Data & Migration", items: [
    { title: "Data migration scripts tested against production-like data", status: "pass" },
    { title: "Rollback migration scripts verified", status: "pass" },
    { title: "Data validation checks pass after migration", status: "pass" },
    { title: "Legacy system cutover plan documented and rehearsed", status: "warning" },
  ]},
  { category: "Compliance", items: [
    { title: "SOC 2 Type II controls documented", status: "pass" },
    { title: "Audit logging verified for all user actions", status: "pass" },
    { title: "Data retention policies configured (90-day audit logs)", status: "pass" },
    { title: "Privacy impact assessment completed", status: "pass" },
  ]},
];

export default function DeployPage() {
  const totalItems = checklistItems.flatMap((c) => c.items);
  const passing = totalItems.filter((i) => i.status === "pass").length;
  const warnings = totalItems.filter((i) => i.status === "warning").length;
  const failing = totalItems.filter((i) => i.status === "fail").length;
  const readinessPercent = Math.round((passing / totalItems.length) * 100);

  return (
    <>
      <Header
        title="Deployment Readiness"
        subtitle="Comprehensive deployment checklist covering infrastructure, security, testing, operations, data migration, and compliance. Every gate must pass before production deployment is authorized."
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Deployment Readiness" },
        ]}
      />

      {/* What is Deployment Readiness */}
      <Card className="mb-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-2xl bg-violet-100 flex items-center justify-center shrink-0">
            <svg className="w-6 h-6 text-violet-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z" />
              <path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z" />
              <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0" />
              <path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-900 mb-2">What Happens in Deployment Readiness</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Deployment Readiness is the final gate before production. The AI compiles a comprehensive checklist covering 
              infrastructure provisioning, security posture, test results, operational readiness, data migration status, and 
              compliance requirements. Each item is automatically validated where possible and manually confirmed where needed. 
              No deployment proceeds without all Critical items passing and all warnings having documented mitigation plans.
            </p>
          </div>
        </div>
      </Card>

      {/* How It Works */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        {[
          { step: "1", title: "Checklist Generation", description: "AI generates a deployment checklist based on the project's architecture, infrastructure, and compliance requirements.", color: "bg-violet-50 border-violet-200" },
          { step: "2", title: "Automated Validation", description: "Infrastructure, security, and testing items are automatically validated against live environments where possible.", color: "bg-purple-50 border-purple-200" },
          { step: "3", title: "Manual Confirmation", description: "Operations, compliance, and business items are manually confirmed by responsible team members.", color: "bg-fuchsia-50 border-fuchsia-200" },
          { step: "4", title: "Go/No-Go Decision", description: "Engineering lead and stakeholders review the complete checklist and make the final go/no-go deployment decision.", color: "bg-pink-50 border-pink-200" },
        ].map((item) => (
          <Card key={item.step} className={`${item.color} border`}>
            <div className="flex items-center gap-2 mb-2">
              <span className="w-7 h-7 rounded-full bg-white flex items-center justify-center text-sm font-bold text-slate-700 shadow-sm">
                {item.step}
              </span>
              <h4 className="text-sm font-semibold text-slate-800">{item.title}</h4>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">{item.description}</p>
          </Card>
        ))}
      </div>

      {/* Readiness Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Card className="text-center">
          <div className={`text-3xl font-bold ${readinessPercent >= 90 ? "text-emerald-600" : readinessPercent >= 70 ? "text-amber-600" : "text-red-600"}`}>
            {readinessPercent}%
          </div>
          <div className="text-xs text-slate-500 mt-1">Overall Readiness</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-emerald-600">{passing}</div>
          <div className="text-xs text-slate-500 mt-1">Passing</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-amber-600">{warnings}</div>
          <div className="text-xs text-slate-500 mt-1">Warnings</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-red-600">{failing}</div>
          <div className="text-xs text-slate-500 mt-1">Failing</div>
        </Card>
      </div>

      {/* Deployment Checklist */}
      {checklistItems.map((category) => {
        const catPassing = category.items.filter((i) => i.status === "pass").length;
        return (
          <Card key={category.category} className="mb-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-semibold text-slate-900">{category.category}</h3>
              <span className="text-xs text-slate-500">{catPassing}/{category.items.length} passing</span>
            </div>
            <div className="space-y-2">
              {category.items.map((item, i) => {
                const icon = item.status === "pass" ? (
                  <div className="w-5 h-5 rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
                    <svg className="w-3 h-3 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                ) : item.status === "warning" ? (
                  <div className="w-5 h-5 rounded-full bg-amber-100 flex items-center justify-center shrink-0">
                    <svg className="w-3 h-3 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01" />
                    </svg>
                  </div>
                ) : (
                  <div className="w-5 h-5 rounded-full bg-red-100 flex items-center justify-center shrink-0">
                    <svg className="w-3 h-3 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </div>
                );
                const bg = item.status === "pass" ? "bg-white" : item.status === "warning" ? "bg-amber-50" : "bg-red-50";
                return (
                  <div key={i} className={`flex items-center gap-3 p-3 ${bg} rounded-xl border border-slate-100`}>
                    {icon}
                    <span className="text-sm text-slate-700">{item.title}</span>
                  </div>
                );
              })}
            </div>
          </Card>
        );
      })}

      {/* Go/No-Go */}
      <Card>
        <h3 className="text-lg font-semibold text-slate-900 mb-3">Go / No-Go Decision</h3>
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center shrink-0 mt-0.5">
              <svg className="w-4 h-4 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-amber-800 mb-1">Conditional Go — {warnings} warnings, {failing} failure</h4>
              <p className="text-sm text-amber-700 mb-2">
                {passing} of {totalItems.length} checks passing. The following items require attention before production deployment:
              </p>
              <ul className="space-y-1">
                {totalItems.filter((i) => i.status !== "pass").map((item, i) => (
                  <li key={i} className="text-xs text-amber-700 flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${item.status === "fail" ? "bg-red-500" : "bg-amber-500"}`}></span>
                    {item.title}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </Card>
    </>
  );
}
