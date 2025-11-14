'use client'
import { formatNumber } from "@/lib/format";

import { useEffect, useState } from 'react'

interface AnimatedNumberProps {
  value: number
  decimals?: number
  prefix?: string
  suffix?: string
  className?: string
}

export function AnimatedNumber({
  value,
  decimals = 0,
  prefix = '',
  suffix = '',
  className = '',
}: AnimatedNumberProps) {
  const [mounted, setMounted] = useState(false)
  const [displayValue, setDisplayValue] = useState(value)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (!mounted) return

    const startValue = displayValue
    const endValue = value
    const duration = 800
    const startTime = Date.now()
    const ease = (t: number) => (t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t)

    const animate = () => {
      const now = Date.now()
      const progress = Math.min((now - startTime) / duration, 1)
      const easedProgress = ease(progress)
      const currentValue = startValue + (endValue - startValue) * easedProgress

      setDisplayValue(currentValue)

      if (progress < 1) {
        requestAnimationFrame(animate)
      }
    }

    animate()
  }, [value, mounted, displayValue])

  const formatted = formatNumber(displayValue, decimals)
  return <span className={`number ${className}`}>{`${prefix}${formatted}${suffix}`}</span>
}
