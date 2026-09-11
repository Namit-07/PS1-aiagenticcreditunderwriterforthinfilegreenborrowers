import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";

import { cn } from "@/lib/utils";

const alertVariants = cva(
  "relative w-full rounded-lg border p-4 text-sm [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:h-4 [&>svg]:w-4 [&>svg~*]:pl-7",
  {
    variants: {
      variant: {
        default: "bg-card text-foreground",
        destructive: "border-danger/30 bg-danger-soft text-foreground [&>svg]:text-danger",
        warning: "border-warning/35 bg-warning-soft text-foreground [&>svg]:text-warning",
        success: "border-success/30 bg-success-soft text-foreground [&>svg]:text-success",
        info: "border-info/30 bg-info-soft text-foreground [&>svg]:text-info",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

const icons = {
  default: Info,
  destructive: XCircle,
  warning: AlertTriangle,
  success: CheckCircle2,
  info: Info,
};

export interface AlertProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, "title">,
    VariantProps<typeof alertVariants> {
  title?: React.ReactNode;
  icon?: boolean;
}

function Alert({ className, variant, title, icon = true, children, ...props }: AlertProps) {
  const Icon = icons[variant ?? "default"];
  return (
    <div role="alert" className={cn(alertVariants({ variant }), className)} {...props}>
      {icon ? <Icon /> : null}
      {title ? <div className="mb-1 font-semibold leading-none">{title}</div> : null}
      {children ? <div className="text-[13px] leading-relaxed text-foreground/85 [&_p]:leading-relaxed">{children}</div> : null}
    </div>
  );
}

export { Alert, alertVariants };
