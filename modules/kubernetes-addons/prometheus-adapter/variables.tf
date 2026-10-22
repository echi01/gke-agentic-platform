variable "enabled" {
  type    = bool
  default = true
}
variable "manage_via_gitops" {
  type    = bool
  default = true
}
variable "values_override" {
  type    = any
  default = {}
}
