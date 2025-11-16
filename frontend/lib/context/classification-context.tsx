'use client'

import { createContext, useContext, useState, ReactNode } from 'react'

export type BetCategory = 'Played' | 'Interesting' | 'To Play' | 'To Analyze' | 'Rejected' | 'Uncategorized'

export interface ClassifiedBet {
  id: number
  type: string
  risk: string
  sport: string
  title: string
  match: string
  odds: string
  recentForm: string[]
  agent: string
  confidence: number
  category: BetCategory
  classifiedAt: Date
}

interface ClassificationContextType {
  classifiedBets: ClassifiedBet[]
  classifiedIds: Set<number>
  addBet: (bet: Omit<ClassifiedBet, 'category' | 'classifiedAt'>) => void
  updateCategory: (betId: number, category: BetCategory) => void
  removeBet: (betId: number) => void
  isClassified: (betId: number) => boolean
}

const ClassificationContext = createContext<ClassificationContextType | undefined>(undefined)

export function ClassificationProvider({ children }: { children: ReactNode }) {
  const [classifiedBets, setClassifiedBets] = useState<ClassifiedBet[]>([])
  const [classifiedIds, setClassifiedIds] = useState<Set<number>>(new Set())

  const addBet = (bet: Omit<ClassifiedBet, 'category' | 'classifiedAt'>) => {
    if (classifiedIds.has(bet.id)) return

    const newBet: ClassifiedBet = {
      ...bet,
      category: 'Uncategorized',
      classifiedAt: new Date(),
    }
    setClassifiedBets((prev) => [...prev, newBet])
    setClassifiedIds((prev) => new Set(prev).add(bet.id))
  }

  const updateCategory = (betId: number, category: BetCategory) => {
    setClassifiedBets((prev) =>
      prev.map((bet) =>
        bet.id === betId ? { ...bet, category } : bet
      )
    )
  }

  const removeBet = (betId: number) => {
    setClassifiedBets((prev) => prev.filter((bet) => bet.id !== betId))
    setClassifiedIds((prev) => {
      const newSet = new Set(prev)
      newSet.delete(betId)
      return newSet
    })
  }

  const isClassified = (betId: number) => {
    return classifiedIds.has(betId)
  }

  return (
    <ClassificationContext.Provider value={{ classifiedBets, classifiedIds, addBet, updateCategory, removeBet, isClassified }}>
      {children}
    </ClassificationContext.Provider>
  )
}

export function useClassification() {
  const context = useContext(ClassificationContext)
  if (!context) {
    throw new Error('useClassification must be used within ClassificationProvider')
  }
  return context
}
