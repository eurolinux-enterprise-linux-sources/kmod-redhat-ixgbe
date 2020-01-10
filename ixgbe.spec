%define kmod_name		ixgbe
%define kmod_vendor		redhat
%define kmod_driver_version	4.4.0_k_rh7.4_z
%define kmod_rpm_release	2
%define kmod_kernel_version	3.10.0-514.el7
%define kmod_kbuild_dir		drivers/net/ethernet/intel/ixgbe

%{!?dist: %define dist .el7_3}

Source0:	%{kmod_name}-%{kmod_vendor}-%{kmod_driver_version}.tar.bz2
# Source code patches
Patch0:	0000-revert-deprecate_dev__trans_start.patch
Patch1:	0001-udp_tunnel_get_rx_info.patch
Patch2:	0002-revert-Update-API-for-VF-vlan-protocol-802_1ad-support.patch
Patch3:	0003-skb_checksum_start.patch
Patch4:	0004-pci_release_mem_regions.patch
Patch5:	0005-csum_replace_by_diff.patch
Patch6:	0006-fake-features.patch
Patch7:	0007-revert-ndo_dflt_bridge_getlink.patch
Patch8:	0008-hlist_add_behind.patch
Patch9:	0009-version-bump.patch

%define findpat %( echo "%""P" )
%define __find_requires /usr/lib/rpm/redhat/find-requires.ksyms
%define __find_provides /usr/lib/rpm/redhat/find-provides.ksyms %{kmod_name} %{?epoch:%{epoch}:}%{version}-%{release}
%define sbindir %( if [ -x "/sbin/weak-modules" ]; then echo "/sbin"; else echo %{_sbindir}; fi )

Name:		kmod-redhat-ixgbe
Version:	%{kmod_driver_version}
Release:	%{kmod_rpm_release}%{?dist}
Summary:	ixgbe module for Driver Update Program
Group:		System/Kernel
License:	GPLv2
URL:		http://www.kernel.org/
BuildRoot:	%(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildRequires:	kernel-devel = %kmod_kernel_version redhat-rpm-config kernel-abi-whitelists
ExclusiveArch:	x86_64
%global kernel_source() /usr/src/kernels/%{kmod_kernel_version}.$(arch)

%global _use_internal_dependency_generator 0
Provides:	kernel-modules = %kmod_kernel_version.%{_target_cpu}
Provides:	%{kmod_name}-kmod = %{?epoch:%{epoch}:}%{version}-%{release}
Requires(post):	%{sbindir}/weak-modules
Requires(postun):	%{sbindir}/weak-modules
Requires:	kernel >= 3.10.0-514.el7
Requires:	kernel < 3.10.0-515.el7
# if there are multiple kmods for the same driver from different vendors,
# they should coflict with each other.
Conflicts:	%{kmod_name}-kmod

%description
ixgbe module for Driver Update Program

%post
modules=( $(find /lib/modules/%{kmod_kernel_version}.%(arch)/extra/kmod-%{kmod_vendor}-%{kmod_name} | grep '\.ko$') )
printf '%s\n' "${modules[@]}" | %{sbindir}/weak-modules --add-modules

%preun
rpm -ql kmod-redhat-ixgbe-%{kmod_driver_version}-%{kmod_rpm_release}%{?dist}.$(arch) | grep '\.ko$' > /var/run/rpm-kmod-%{kmod_name}-modules

%postun
modules=( $(cat /var/run/rpm-kmod-%{kmod_name}-modules) )
rm /var/run/rpm-kmod-%{kmod_name}-modules
printf '%s\n' "${modules[@]}" | %{sbindir}/weak-modules --remove-modules

%files
%defattr(644,root,root,755)
/lib/modules/%{kmod_kernel_version}.%(arch)
/etc/depmod.d/ixgbe.conf
/usr/share/doc/kmod-ixgbe/greylist.txt

%prep
%setup -n ixgbe-redhat-4.4.0_k_rh7.4_z

%patch0 -p1
%patch1 -p1
%patch2 -p1
%patch3 -p1
%patch4 -p1
%patch5 -p1
%patch6 -p1
%patch7 -p1
%patch8 -p1
%patch9 -p1
set -- *
mkdir source
mv "$@" source/
mkdir obj

%build
rm -rf obj
cp -r source obj
make -C %{kernel_source} M=$PWD/obj/%{kmod_kbuild_dir} \
	NOSTDINC_FLAGS="-I $PWD/obj/include"
# mark modules executable so that strip-to-file can strip them
find obj/%{kmod_kbuild_dir} -name "*.ko" -type f -exec chmod u+x '{}' +

whitelist="/lib/modules/kabi-current/kabi_whitelist_%{_target_cpu}"
for modules in $( find obj/%{kmod_kbuild_dir} -name "*.ko" -type f -printf "%{findpat}\n" | sed 's|\.ko$||' | sort -u ) ; do
	# update depmod.conf
	module_weak_path=$(echo $modules | sed 's/[\/]*[^\/]*$//')
	if [ -z "$module_weak_path" ]; then
		module_weak_path=%{name}
	else
		module_weak_path=%{name}/$module_weak_path
	fi
	echo "override $(echo $modules | sed 's/.*\///') $(echo %{kmod_kernel_version} | sed 's/\.[^\.]*$//').* weak-updates/$module_weak_path" >> source/depmod.conf

	# update greylist
	nm -u obj/%{kmod_kbuild_dir}/$modules.ko | sed 's/.*U //' |  sed 's/^\.//' | sort -u | while read -r symbol; do
		grep -q "^\s*$symbol\$" $whitelist || echo "$symbol" >> source/greylist
	done
done
sort -u source/greylist | uniq > source/greylist.txt

%install
export INSTALL_MOD_PATH=$RPM_BUILD_ROOT
export INSTALL_MOD_DIR=extra/%{name}
make -C %{kernel_source} modules_install \
	M=$PWD/obj/%{kmod_kbuild_dir}
# Cleanup unnecessary kernel-generated module dependency files.
find $INSTALL_MOD_PATH/lib/modules -iname 'modules.*' -exec rm {} \;

install -m 644 -D source/depmod.conf $RPM_BUILD_ROOT/etc/depmod.d/%{kmod_name}.conf
install -m 644 -D source/greylist.txt $RPM_BUILD_ROOT/usr/share/doc/kmod-%{kmod_name}/greylist.txt

%clean
rm -rf $RPM_BUILD_ROOT

%changelog
* Fri Apr 07 2017 Eugene Syromiatnikov <esyr@redhat.com> 4.4.0_k_rh7.4_z-2
- Remove testing desclaimer from the package description
- 6591372b59cec0e59cd144bed3e51ba8ceb2dd88
- ixgbe module for Driver Update Program
- Resolves: #bz1439814

* Mon Mar 13 2017 Eugene Syromiatnikov <esyr@redhat.com> 4.4.0_k_rh7.4_z-1
- 6591372b59cec0e59cd144bed3e51ba8ceb2dd88
- ixgbe module for Driver Update Program
- Resolves: #bz1439814
