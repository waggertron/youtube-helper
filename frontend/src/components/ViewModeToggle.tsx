import { ToggleButton, ToggleButtonGroup } from '@mui/material'
import { ViewModule, ViewList, TableRows } from '@mui/icons-material'

export type ViewMode = 'grid' | 'list' | 'compact'

interface ViewModeToggleProps {
  value: ViewMode
  onChange: (mode: ViewMode) => void
}

export default function ViewModeToggle({ value, onChange }: ViewModeToggleProps) {
  return (
    <ToggleButtonGroup
      value={value}
      exclusive
      onChange={(_e, newMode) => { if (newMode) onChange(newMode) }}
      size="small"
    >
      <ToggleButton value="grid" aria-label="Grid view">
        <ViewModule />
      </ToggleButton>
      <ToggleButton value="list" aria-label="List view">
        <ViewList />
      </ToggleButton>
      <ToggleButton value="compact" aria-label="Compact view">
        <TableRows />
      </ToggleButton>
    </ToggleButtonGroup>
  )
}
