

resource "oci_core_instance" "starter_bastion" {

  availability_domain = data.oci_identity_availability_domain.ad.name
  compartment_id      = local.lz_web_cmp_ocid
  display_name        = "${var.prefix}-bastion"
  shape               = var.instance_shape

  shape_config {
    ocpus         = var.instance_ocpus
    memory_in_gbs = var.instance_shape_config_memory_in_gbs
  }

  create_vnic_details {
    subnet_id                 = data.oci_core_subnet.starter_web_subnet.id
    display_name              = "Primaryvnic"
    assign_public_ip          = true
    assign_private_dns_record = true
    hostname_label            = "${var.prefix}-bastion"
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
  }

  source_details {
    source_type = "image"
    # boot_volume_size_in_gbs = "50" 
    source_id   = data.oci_core_images.oraclelinux.images.0.id
  }

  connection {
    agent       = false
    host        = oci_core_instance.starter_bastion.public_ip
    user        = "opc"
    private_key = var.ssh_private_key
  }

  lifecycle {
    ignore_changes = [
      source_details[0].source_id,
      shape
    ]
  }

  freeform_tags = local.freeform_tags   
}

data "oci_core_instance" "starter_bastion" {
  instance_id = oci_core_instance.starter_bastion.id
}

locals {
  local_bastion_ip = data.oci_core_instance.starter_bastion.public_ip
}

output "bastion_ip" {
  value = local.local_bastion_ip
}