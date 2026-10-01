import React from "react";
import { motion, useReducedMotion } from "framer-motion";

interface FloatingProps {
  children: React.ReactNode;
  duration?: number;
  distance?: number;
  className?: string;
}

export const Floating: React.FC<FloatingProps> = ({
  children,
  duration = 3,
  distance = 8,
  className = "",
}) => {
  const shouldReduceMotion = useReducedMotion();

  if (shouldReduceMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      animate={{
        y: [-distance / 2, distance / 2, -distance / 2],
      }}
      transition={{
        duration,
        repeat: Infinity,
        ease: "easeInOut",
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
};
