'use client';

import * as React from 'react';
import Link from 'next/link';
import { useTheme } from 'next-themes';
import type { ColumnDef } from '@tanstack/react-table';
import {
  AlertCircle,
  ArrowRight,
  Check,
  ChevronDown,
  FileText,
  Inbox,
  Mail,
  Moon,
  Plus,
  Search,
  Settings,
  Sun,
  Trash2,
  User,
} from 'lucide-react';

import { Alert } from '@/components/ui/alert';
import {
  Avatar,
  AvatarGroup,
  type AvatarSize,
  type AvatarStatus,
} from '@/components/ui/avatar';
import { Badge, type BadgeColor, type BadgeSize } from '@/components/ui/badge';
import {
  Breadcrumb,
  BreadcrumbEllipsis,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import {
  Button,
  type ButtonSize,
  type ButtonVariant,
} from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown';
import { EmptyState, FeaturedIcon } from '@/components/ui/empty-state';
import { Input } from '@/components/ui/input';
import { PaginationControl } from '@/components/ui/pagination';
import { RadioGroup, RadioItem } from '@/components/ui/radio';
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Skeleton,
  SkeletonAvatar,
  SkeletonCard,
  SkeletonText,
} from '@/components/ui/skeleton';
import { Spinner } from '@/components/ui/spinner';
import { Switch } from '@/components/ui/switch';
import {
  DataTable,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

// ─── Section helpers ──────────────────────────────────────────────────────

interface SectionProps {
  id: string;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}

function Section({ id, title, subtitle, children }: SectionProps) {
  return (
    <section id={id} className="scroll-mt-24">
      <div className="mb-4">
        <h2 className="text-2xl font-semibold text-foreground">{title}</h2>
        {subtitle && (
          <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
        )}
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">{children}</div>
    </section>
  );
}

interface ExampleProps {
  label: string;
  children: React.ReactNode;
  full?: boolean;
}

function Example({ label, children, full }: ExampleProps) {
  return (
    <Card className={full ? 'md:col-span-2' : undefined}>
      <CardHeader>
        <CardTitle className="text-sm font-medium">{label}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-wrap items-start gap-3">
        {children}
      </CardContent>
    </Card>
  );
}

// ─── Mock data ─────────────────────────────────────────────────────────────

type Person = {
  id: number;
  name: string;
  email: string;
  role: string;
  status: 'Active' | 'Invited' | 'Suspended' | 'Archived';
};

const people: Person[] = [
  {
    id: 1,
    name: 'Olivia Rhye',
    email: 'olivia@untitledui.com',
    role: 'Designer',
    status: 'Active',
  },
  {
    id: 2,
    name: 'Phoenix Baker',
    email: 'phoenix@untitledui.com',
    role: 'Product Manager',
    status: 'Active',
  },
  {
    id: 3,
    name: 'Lana Steiner',
    email: 'lana@untitledui.com',
    role: 'Frontend Engineer',
    status: 'Invited',
  },
  {
    id: 4,
    name: 'Demi Wilkinson',
    email: 'demi@untitledui.com',
    role: 'Backend Engineer',
    status: 'Suspended',
  },
  {
    id: 5,
    name: 'Candice Wu',
    email: 'candice@untitledui.com',
    role: 'Designer',
    status: 'Archived',
  },
];

const statusToColor: Record<Person['status'], BadgeColor> = {
  Active: 'success',
  Invited: 'blue',
  Suspended: 'warning',
  Archived: 'gray',
};

const personColumns: ColumnDef<Person, unknown>[] = [
  { accessorKey: 'name', header: 'Name' },
  { accessorKey: 'email', header: 'Email' },
  { accessorKey: 'role', header: 'Role' },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ getValue }) => {
      const v = getValue<Person['status']>();
      return (
        <Badge color={statusToColor[v]} dot size="sm">
          {v}
        </Badge>
      );
    },
  },
];

// ─── Page-level constants ──────────────────────────────────────────────────

const buttonVariants: ButtonVariant[] = [
  'primary',
  'secondary',
  'tertiary',
  'link-gray',
  'link-color',
  'destructive',
  'destructive-secondary',
];

const buttonSizes: ButtonSize[] = ['sm', 'md', 'lg', 'xl'];

const badgeColors: BadgeColor[] = [
  'gray',
  'brand',
  'error',
  'warning',
  'success',
  'blue',
];

const badgeSizes: BadgeSize[] = ['sm', 'md', 'lg'];

const avatarSizes: AvatarSize[] = ['xs', 'sm', 'md', 'lg', 'xl', '2xl'];
const avatarStatuses: AvatarStatus[] = ['online', 'offline', 'busy', 'away'];

const toc: Array<{ id: string; label: string }> = [
  { id: 'buttons', label: 'Buttons' },
  { id: 'inputs', label: 'Inputs' },
  { id: 'textareas', label: 'Textarea' },
  { id: 'selects', label: 'Select' },
  { id: 'checkboxes', label: 'Checkbox' },
  { id: 'radios', label: 'Radio' },
  { id: 'switches', label: 'Switch' },
  { id: 'cards', label: 'Card' },
  { id: 'badges', label: 'Badge' },
  { id: 'avatars', label: 'Avatar' },
  { id: 'tabs', label: 'Tabs' },
  { id: 'dialogs', label: 'Dialog' },
  { id: 'dropdowns', label: 'Dropdown' },
  { id: 'tooltips', label: 'Tooltip' },
  { id: 'alerts', label: 'Alert' },
  { id: 'skeletons', label: 'Skeleton' },
  { id: 'spinners', label: 'Spinner' },
  { id: 'tables', label: 'Table' },
  { id: 'empty-states', label: 'Empty State' },
  { id: 'breadcrumbs', label: 'Breadcrumb' },
  { id: 'pagination', label: 'Pagination' },
];

// ─── Page ──────────────────────────────────────────────────────────────────

export default function PlaygroundPage() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);
  const [checked, setChecked] = React.useState(false);
  const [indeterminate, setIndeterminate] = React.useState<
    boolean | 'indeterminate'
  >('indeterminate');
  const [radio, setRadio] = React.useState('one');
  const [switchOn, setSwitchOn] = React.useState(true);
  const [page, setPage] = React.useState(3);
  const [pageSize, setPageSize] = React.useState(10);
  const [showNotifications, setShowNotifications] = React.useState(true);
  const [showShortcuts, setShowShortcuts] = React.useState(false);
  const [sort, setSort] = React.useState('name');

  React.useEffect(() => {
    setMounted(true);
  }, []);

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  };

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-background text-foreground">
        {/* Header */}
        <header className="sticky top-0 z-30 border-b border-border bg-background/80 backdrop-blur">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">
                Component Playground
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Every Untitled UI primitive in every variant, for visual review.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                leadingIcon={
                  mounted ? (
                    theme === 'dark' ? (
                      <Sun className="h-4 w-4" />
                    ) : (
                      <Moon className="h-4 w-4" />
                    )
                  ) : null
                }
                onClick={toggleTheme}
                aria-label="Toggle theme"
              >
                {mounted ? (theme === 'dark' ? 'Light' : 'Dark') : 'Theme'}
              </Button>
              <Link href="/">
                <Button variant="tertiary" size="sm" trailingIcon={<ArrowRight className="h-4 w-4" />}>
                  Back to app
                </Button>
              </Link>
            </div>
          </div>
        </header>

        <div className="mx-auto flex max-w-7xl gap-8 px-6 py-8">
          {/* TOC */}
          <aside className="sticky top-24 hidden h-[calc(100vh-7rem)] w-56 shrink-0 overflow-y-auto md:block">
            <nav aria-label="Table of contents" className="flex flex-col gap-1">
              <p className="px-2 pb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Components
              </p>
              {toc.map((item) => (
                <a
                  key={item.id}
                  href={`#${item.id}`}
                  className="rounded-md px-2 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                >
                  {item.label}
                </a>
              ))}
            </nav>
          </aside>

          {/* Main content */}
          <main className="flex min-w-0 flex-1 flex-col gap-12">
            {/* Buttons */}
            <Section
              id="buttons"
              title="Buttons"
              subtitle="All variants × all sizes, plus loading/disabled/icon states."
            >
              {buttonVariants.map((variant) => (
                <Example key={variant} label={`variant="${variant}"`}>
                  {buttonSizes.map((size) => (
                    <Button
                      key={size}
                      variant={variant}
                      size={size}
                      autoFocus={variant === 'primary' && size === 'md'}
                    >
                      {variant}/{size}
                    </Button>
                  ))}
                </Example>
              ))}
              <Example label="Icon-only & icons in buttons">
                <Button variant="primary" size="icon" aria-label="Add">
                  <Plus className="h-4 w-4" />
                </Button>
                <Button variant="secondary" size="icon" aria-label="Settings">
                  <Settings className="h-4 w-4" />
                </Button>
                <Button variant="primary" leadingIcon={<Plus className="h-4 w-4" />}>
                  Create new
                </Button>
                <Button
                  variant="secondary"
                  trailingIcon={<ArrowRight className="h-4 w-4" />}
                >
                  Continue
                </Button>
              </Example>
              <Example label="Loading & disabled">
                <Button variant="primary" loading>
                  Saving…
                </Button>
                <Button variant="secondary" loading>
                  Loading
                </Button>
                <Button variant="primary" disabled>
                  Disabled
                </Button>
                <Button variant="destructive" disabled>
                  Disabled
                </Button>
              </Example>
            </Section>

            {/* Inputs */}
            <Section
              id="inputs"
              title="Input"
              subtitle="Sizes sm/md/lg, label/hint/error, leading & trailing icons."
            >
              <Example label="Sizes">
                <Input inputSize="sm" placeholder="Small input" label="Small" />
                <Input inputSize="md" placeholder="Medium input" label="Medium" />
                <Input inputSize="lg" placeholder="Large input" label="Large" />
              </Example>
              <Example label="States">
                <Input label="Default" placeholder="you@example.com" hint="We never share your email." />
                <Input label="With error" placeholder="you@example.com" error="Enter a valid email" defaultValue="not-an-email" />
                <Input label="Disabled" placeholder="Disabled" disabled defaultValue="Read only" />
              </Example>
              <Example label="With icons" full>
                <Input
                  label="Search"
                  placeholder="Search…"
                  leadingIcon={<Search />}
                />
                <Input
                  label="Email"
                  placeholder="you@example.com"
                  leadingIcon={<Mail />}
                  trailingIcon={<Check />}
                />
              </Example>
            </Section>

            {/* Textarea */}
            <Section
              id="textareas"
              title="Textarea"
              subtitle="Auto-grow, character counter, error state."
            >
              <Example label="Default">
                <Textarea
                  label="Description"
                  placeholder="Tell us a bit…"
                  hint="Markdown supported."
                />
              </Example>
              <Example label="With character counter">
                <Textarea
                  label="Bio"
                  placeholder="A short bio"
                  maxLength={140}
                  showCounter
                  defaultValue="Designer & maker."
                />
              </Example>
              <Example label="Auto-grow">
                <Textarea
                  label="Notes"
                  placeholder="Type a lot…"
                  autoGrow
                />
              </Example>
              <Example label="Error & disabled">
                <Textarea label="Error" error="This field is required" />
                <Textarea label="Disabled" disabled defaultValue="Cannot edit" />
              </Example>
            </Section>

            {/* Select */}
            <Section
              id="selects"
              title="Select"
              subtitle="Radix-based select with groups and labels."
            >
              <Example label="Default">
                <div className="w-64">
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Choose a fruit" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        <SelectLabel>Fruits</SelectLabel>
                        <SelectItem value="apple">Apple</SelectItem>
                        <SelectItem value="banana">Banana</SelectItem>
                        <SelectItem value="orange">Orange</SelectItem>
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                </div>
              </Example>
              <Example label="Disabled & error">
                <div className="w-64">
                  <Select disabled>
                    <SelectTrigger>
                      <SelectValue placeholder="Disabled" />
                    </SelectTrigger>
                    <SelectContent />
                  </Select>
                </div>
                <div className="w-64">
                  <Select>
                    <SelectTrigger error>
                      <SelectValue placeholder="Error state" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="a">Option A</SelectItem>
                      <SelectItem value="b">Option B</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </Example>
            </Section>

            {/* Checkbox */}
            <Section
              id="checkboxes"
              title="Checkbox"
              subtitle="With label, description, indeterminate & disabled."
            >
              <Example label="States">
                <Checkbox label="Unchecked" />
                <Checkbox label="Checked" defaultChecked />
                <Checkbox
                  label="Indeterminate"
                  checked={indeterminate}
                  onCheckedChange={setIndeterminate}
                />
                <Checkbox label="Disabled" disabled />
                <Checkbox label="Disabled checked" disabled defaultChecked />
              </Example>
              <Example label="With description">
                <Checkbox
                  label="Email notifications"
                  description="Get an email when someone mentions you."
                  checked={checked}
                  onCheckedChange={(v) => setChecked(v === true)}
                />
              </Example>
            </Section>

            {/* Radio */}
            <Section
              id="radios"
              title="Radio"
              subtitle="RadioGroup + RadioItem with label & description."
            >
              <Example label="Group" full>
                <RadioGroup value={radio} onValueChange={setRadio}>
                  <RadioItem value="one" label="Option one" description="The first option." />
                  <RadioItem value="two" label="Option two" description="The second option." />
                  <RadioItem value="three" label="Option three" disabled description="Disabled option." />
                </RadioGroup>
              </Example>
            </Section>

            {/* Switch */}
            <Section
              id="switches"
              title="Switch"
              subtitle="Two sizes, with label & description."
            >
              <Example label="Sizes">
                <Switch switchSize="sm" label="Small" />
                <Switch switchSize="md" label="Medium" defaultChecked />
              </Example>
              <Example label="States">
                <Switch
                  label="Notifications"
                  description="Receive product updates."
                  checked={switchOn}
                  onCheckedChange={setSwitchOn}
                />
                <Switch label="Disabled" disabled />
                <Switch label="Disabled on" disabled defaultChecked />
              </Example>
            </Section>

            {/* Card */}
            <Section
              id="cards"
              title="Card"
              subtitle="Card + Header + Title + Description + Content + Footer."
            >
              <Example label="With footer" full>
                <Card className="w-full">
                  <CardHeader>
                    <CardTitle>Project settings</CardTitle>
                    <CardDescription>
                      Manage your project's general configuration.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">
                      Card content area, used for body text, forms, lists, etc.
                    </p>
                  </CardContent>
                  <CardFooter>
                    <Button variant="secondary">Cancel</Button>
                    <Button variant="primary">Save changes</Button>
                  </CardFooter>
                </Card>
              </Example>
            </Section>

            {/* Badge */}
            <Section
              id="badges"
              title="Badge"
              subtitle="All colors × all sizes, with dot, icon and closable."
            >
              {badgeColors.map((color) => (
                <Example key={color} label={`color="${color}"`}>
                  {badgeSizes.map((size) => (
                    <Badge key={size} color={color} size={size}>
                      {color}/{size}
                    </Badge>
                  ))}
                  <Badge color={color} dot>
                    dot
                  </Badge>
                  <Badge
                    color={color}
                    leadingIcon={<Check />}
                  >
                    icon
                  </Badge>
                  <Badge color={color} onClose={() => {}}>
                    removable
                  </Badge>
                </Example>
              ))}
            </Section>

            {/* Avatar */}
            <Section
              id="avatars"
              title="Avatar"
              subtitle="All sizes, status indicators and AvatarGroup."
            >
              <Example label="Sizes" full>
                {avatarSizes.map((size) => (
                  <Avatar
                    key={size}
                    size={size}
                    src="https://i.pravatar.cc/150?img=12"
                    alt="Olivia"
                    fallback="OR"
                  />
                ))}
              </Example>
              <Example label="Fallback initials">
                {avatarSizes.map((size) => (
                  <Avatar key={size} size={size} fallback="OR" />
                ))}
              </Example>
              <Example label="Status indicators">
                {avatarStatuses.map((status) => (
                  <Avatar
                    key={status}
                    size="lg"
                    status={status}
                    fallback="AB"
                  />
                ))}
              </Example>
              <Example label="AvatarGroup with max" full>
                <AvatarGroup max={3}>
                  <Avatar fallback="OR" />
                  <Avatar fallback="PB" />
                  <Avatar fallback="LS" />
                  <Avatar fallback="DW" />
                  <Avatar fallback="CW" />
                </AvatarGroup>
              </Example>
            </Section>

            {/* Tabs */}
            <Section id="tabs" title="Tabs" subtitle="Three variants.">
              {(['underline', 'pill', 'button-group'] as const).map((variant) => (
                <Example key={variant} label={`variant="${variant}"`} full>
                  <Tabs defaultValue="overview" variant={variant} className="w-full">
                    <TabsList>
                      <TabsTrigger value="overview">Overview</TabsTrigger>
                      <TabsTrigger value="activity">Activity</TabsTrigger>
                      <TabsTrigger value="members">Members</TabsTrigger>
                      <TabsTrigger value="settings" disabled>
                        Settings
                      </TabsTrigger>
                    </TabsList>
                    <TabsContent value="overview" className="p-4 text-sm text-muted-foreground">
                      Overview content
                    </TabsContent>
                    <TabsContent value="activity" className="p-4 text-sm text-muted-foreground">
                      Activity content
                    </TabsContent>
                    <TabsContent value="members" className="p-4 text-sm text-muted-foreground">
                      Members content
                    </TabsContent>
                  </Tabs>
                </Example>
              ))}
            </Section>

            {/* Dialog */}
            <Section
              id="dialogs"
              title="Dialog"
              subtitle="Sizes sm/md/lg — click a trigger to open."
            >
              {(['sm', 'md', 'lg'] as const).map((size) => (
                <Example key={size} label={`size="${size}"`}>
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button variant="secondary">Open {size} dialog</Button>
                    </DialogTrigger>
                    <DialogContent size={size}>
                      <DialogHeader>
                        <DialogTitle>Confirm action</DialogTitle>
                        <DialogDescription>
                          Are you sure you want to proceed? This action can't be
                          undone.
                        </DialogDescription>
                      </DialogHeader>
                      <DialogBody>
                        Optional body content goes here. Long text wraps neatly
                        inside the dialog body.
                      </DialogBody>
                      <DialogFooter>
                        <Button variant="secondary">Cancel</Button>
                        <Button variant="primary">Confirm</Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                </Example>
              ))}
            </Section>

            {/* Dropdown */}
            <Section
              id="dropdowns"
              title="Dropdown"
              subtitle="Items, checkbox, radio, label, separator, shortcut and submenu."
            >
              <Example label="Full menu" full>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="secondary" trailingIcon={<ChevronDown className="h-4 w-4" />}>
                      Open menu
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start" className="w-64">
                    <DropdownMenuLabel>My account</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem>
                      <User className="h-4 w-4" /> Profile
                      <DropdownMenuShortcut>⇧⌘P</DropdownMenuShortcut>
                    </DropdownMenuItem>
                    <DropdownMenuItem>
                      <Settings className="h-4 w-4" /> Settings
                      <DropdownMenuShortcut>⌘,</DropdownMenuShortcut>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuLabel>Preferences</DropdownMenuLabel>
                    <DropdownMenuCheckboxItem
                      checked={showNotifications}
                      onCheckedChange={setShowNotifications}
                    >
                      Notifications
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={showShortcuts}
                      onCheckedChange={setShowShortcuts}
                    >
                      Keyboard shortcuts
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuLabel>Sort</DropdownMenuLabel>
                    <DropdownMenuRadioGroup value={sort} onValueChange={setSort}>
                      <DropdownMenuRadioItem value="name">
                        Name
                      </DropdownMenuRadioItem>
                      <DropdownMenuRadioItem value="date">
                        Date
                      </DropdownMenuRadioItem>
                      <DropdownMenuRadioItem value="size">
                        Size
                      </DropdownMenuRadioItem>
                    </DropdownMenuRadioGroup>
                    <DropdownMenuSeparator />
                    <DropdownMenuSub>
                      <DropdownMenuSubTrigger>
                        More options
                      </DropdownMenuSubTrigger>
                      <DropdownMenuSubContent>
                        <DropdownMenuItem>Share</DropdownMenuItem>
                        <DropdownMenuItem>Move</DropdownMenuItem>
                        <DropdownMenuItem>Duplicate</DropdownMenuItem>
                      </DropdownMenuSubContent>
                    </DropdownMenuSub>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem destructive>
                      <Trash2 className="h-4 w-4" /> Delete
                      <DropdownMenuShortcut>⌫</DropdownMenuShortcut>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </Example>
            </Section>

            {/* Tooltip */}
            <Section
              id="tooltips"
              title="Tooltip"
              subtitle="Hover or focus a trigger."
            >
              <Example label="Sides" full>
                {(['top', 'right', 'bottom', 'left'] as const).map((side) => (
                  <Tooltip key={side}>
                    <TooltipTrigger asChild>
                      <Button variant="secondary">{side}</Button>
                    </TooltipTrigger>
                    <TooltipContent side={side}>
                      Tooltip on {side}
                    </TooltipContent>
                  </Tooltip>
                ))}
              </Example>
            </Section>

            {/* Alert */}
            <Section
              id="alerts"
              title="Alert"
              subtitle="Four variants with title, description, actions and dismiss."
            >
              {(['info', 'success', 'warning', 'error'] as const).map((variant) => (
                <Example key={variant} label={`variant="${variant}"`} full>
                  <Alert
                    variant={variant}
                    title={`${variant[0].toUpperCase()}${variant.slice(1)} title`}
                    description="A short supporting description that explains the alert in more detail."
                    actions={
                      <>
                        <Button variant="link-color" size="sm">
                          Learn more
                        </Button>
                        <Button variant="tertiary" size="sm">
                          Dismiss
                        </Button>
                      </>
                    }
                    onClose={() => {}}
                    className="w-full"
                  />
                </Example>
              ))}
            </Section>

            {/* Skeleton */}
            <Section
              id="skeletons"
              title="Skeleton"
              subtitle="Base, text, avatar and card variants."
            >
              <Example label="Skeleton + SkeletonText">
                <div className="w-full space-y-3">
                  <Skeleton className="h-6 w-1/3" />
                  <SkeletonText lines={4} />
                </div>
              </Example>
              <Example label="SkeletonAvatar (all sizes)">
                {(['xs', 'sm', 'md', 'lg', 'xl'] as const).map((s) => (
                  <SkeletonAvatar key={s} size={s} />
                ))}
              </Example>
              <Example label="SkeletonCard" full>
                <div className="grid w-full grid-cols-1 gap-4 md:grid-cols-2">
                  <SkeletonCard />
                  <SkeletonCard showImage />
                </div>
              </Example>
            </Section>

            {/* Spinner */}
            <Section id="spinners" title="Spinner" subtitle="Sizes × colors.">
              <Example label="Sizes">
                {(['xs', 'sm', 'md', 'lg'] as const).map((s) => (
                  <Spinner key={s} size={s} />
                ))}
              </Example>
              <Example label="Colors">
                <Spinner color="primary" />
                <Spinner color="gray" />
                <div className="rounded-md bg-gray-900 p-2">
                  <Spinner color="white" />
                </div>
              </Example>
            </Section>

            {/* Table */}
            <Section
              id="tables"
              title="Table"
              subtitle="Primitives + DataTable with 5-row mock dataset."
            >
              <Example label="Primitive Table" full>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {people.map((p) => (
                      <TableRow key={p.id}>
                        <TableCell>{p.name}</TableCell>
                        <TableCell>{p.email}</TableCell>
                        <TableCell>{p.role}</TableCell>
                        <TableCell>
                          <Badge color={statusToColor[p.status]} dot size="sm">
                            {p.status}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Example>
              <Example label="DataTable" full>
                <DataTable<Person>
                  data={people}
                  columns={personColumns}
                  pageSize={10}
                />
              </Example>
            </Section>

            {/* Empty state */}
            <Section
              id="empty-states"
              title="Empty state & FeaturedIcon"
              subtitle="Standalone featured icons + a full empty state."
            >
              <Example label="FeaturedIcon — colors" full>
                {(['brand', 'gray', 'success', 'warning', 'error', 'info'] as const).map(
                  (color) => (
                    <FeaturedIcon
                      key={color}
                      color={color}
                      size="md"
                      icon={<Inbox />}
                    />
                  )
                )}
              </Example>
              <Example label="FeaturedIcon — sizes">
                {(['sm', 'md', 'lg'] as const).map((size) => (
                  <FeaturedIcon
                    key={size}
                    size={size}
                    color="brand"
                    icon={<FileText />}
                  />
                ))}
              </Example>
              <Example label="EmptyState" full>
                <EmptyState
                  className="w-full"
                  icon={<Inbox />}
                  title="No messages yet"
                  description="When you receive new messages they will appear here. Try sending an invitation to get started."
                  actions={
                    <>
                      <Button variant="secondary">Learn more</Button>
                      <Button
                        variant="primary"
                        leadingIcon={<Plus className="h-4 w-4" />}
                      >
                        New message
                      </Button>
                    </>
                  }
                />
              </Example>
            </Section>

            {/* Breadcrumb */}
            <Section id="breadcrumbs" title="Breadcrumb" subtitle="Link, page, separator and ellipsis.">
              <Example label="Default" full>
                <Breadcrumb>
                  <BreadcrumbList>
                    <BreadcrumbItem>
                      <BreadcrumbLink href="#">Home</BreadcrumbLink>
                    </BreadcrumbItem>
                    <BreadcrumbSeparator />
                    <BreadcrumbItem>
                      <BreadcrumbLink href="#">Projects</BreadcrumbLink>
                    </BreadcrumbItem>
                    <BreadcrumbSeparator />
                    <BreadcrumbItem>
                      <BreadcrumbEllipsis />
                    </BreadcrumbItem>
                    <BreadcrumbSeparator />
                    <BreadcrumbItem>
                      <BreadcrumbLink href="#">Settings</BreadcrumbLink>
                    </BreadcrumbItem>
                    <BreadcrumbSeparator />
                    <BreadcrumbItem>
                      <BreadcrumbPage>Billing</BreadcrumbPage>
                    </BreadcrumbItem>
                  </BreadcrumbList>
                </Breadcrumb>
              </Example>
            </Section>

            {/* Pagination */}
            <Section
              id="pagination"
              title="Pagination"
              subtitle="PaginationControl composite with page size & jump-to."
            >
              <Example label="PaginationControl" full>
                <PaginationControl
                  page={page}
                  pageCount={12}
                  totalItems={120}
                  pageSize={pageSize}
                  onPageChange={setPage}
                  onPageSizeChange={setPageSize}
                  showJumpTo
                />
              </Example>
            </Section>

            <footer className="mt-8 border-t border-border pt-6 text-sm text-muted-foreground">
              <p className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4" />
                Playground page — not part of production navigation. Components
                rendered: {toc.length}.
              </p>
            </footer>
          </main>
        </div>
      </div>
    </TooltipProvider>
  );
}
