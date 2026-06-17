USE NewHireCompanyManager;
GO

EXEC dbo.uspCompany_Save
    @IsNewCompany = 1,
    @CompanyIdentifier = N'ACME-001',
    @CompanyName = N'Acme Payroll Services',
    @Address1 = N'100 Market Street',
    @Address2 = N'Suite 250',
    @City = N'Philadelphia',
    @State = N'PA',
    @Zip = N'19106',
    @PhoneNumber = N'215-555-0110',
    @PrimaryContact = N'Maria Alvarez',
    @PointOfContactEmail = N'maria.alvarez@acmepayroll.example',
    @TaxId = N'12-3456789',
    @BankName = N'First National Bank',
    @Form1099 = 1,
    @WithholdingNumber = N'WH-PA-1001',
    @County = N'Philadelphia';
GO

EXEC dbo.uspModule_Save N'ACME-001', N'ABR', 1;
EXEC dbo.uspModule_Save N'ACME-001', N'Accounts Payable', 1;
EXEC dbo.uspModule_Save N'ACME-001', N'Benefits Portal', 1;
EXEC dbo.uspModule_Save N'ACME-001', N'W2 Processing', 1;
GO

EXEC dbo.uspCompany_Save
    @IsNewCompany = 1,
    @CompanyIdentifier = N'BRGT-002',
    @CompanyName = N'BrightPath Logistics',
    @Address1 = N'42 Commerce Drive',
    @Address2 = NULL,
    @City = N'Columbus',
    @State = N'OH',
    @Zip = N'43215',
    @PhoneNumber = N'614-555-0184',
    @PrimaryContact = N'Jordan Lee',
    @PointOfContactEmail = N'jordan.lee@brightpath.example',
    @TaxId = N'98-7654321',
    @BankName = N'Central Trust',
    @Form1099 = 0,
    @WithholdingNumber = N'WH-OH-2202',
    @County = N'Franklin';
GO

EXEC dbo.uspModule_Save N'BRGT-002', N'Contracts', 1;
EXEC dbo.uspModule_Save N'BRGT-002', N'Document Box', 1;
EXEC dbo.uspModule_Save N'BRGT-002', N'Transportation', 1;
GO

EXEC dbo.uspCompany_Save
    @IsNewCompany = 1,
    @CompanyIdentifier = N'NOVA-003',
    @CompanyName = N'NovaCare Staffing',
    @Address1 = N'7800 Lakeview Parkway',
    @Address2 = N'Building B',
    @City = N'Austin',
    @State = N'TX',
    @Zip = N'78701',
    @PhoneNumber = N'512-555-0137',
    @PrimaryContact = N'Sam Patel',
    @PointOfContactEmail = N'sam.patel@novacare.example',
    @TaxId = N'45-6789012',
    @BankName = N'Lone Star Bank',
    @Form1099 = 1,
    @WithholdingNumber = N'WH-TX-3303',
    @County = N'Travis';
GO

EXEC dbo.uspModule_Save N'NOVA-003', N'ACA', 1;
EXEC dbo.uspModule_Save N'NOVA-003', N'OnBoarding/Tasks', 1;
EXEC dbo.uspModule_Save N'NOVA-003', N'Profile/Demographic', 1;
EXEC dbo.uspModule_Save N'NOVA-003', N'Total Compensation', 1;
GO

EXEC dbo.uspCompany_Save
    @IsNewCompany = 1,
    @CompanyIdentifier = N'GRNF-004',
    @CompanyName = N'Greenfield Manufacturing',
    @Address1 = N'305 Industrial Avenue',
    @Address2 = NULL,
    @City = N'Grand Rapids',
    @State = N'MI',
    @Zip = N'49503',
    @PhoneNumber = N'616-555-0199',
    @PrimaryContact = N'Elena Brooks',
    @PointOfContactEmail = N'elena.brooks@greenfield.example',
    @TaxId = N'34-5678901',
    @BankName = N'Great Lakes Credit Union',
    @Form1099 = 0,
    @WithholdingNumber = N'WH-MI-4404',
    @County = N'Kent';
GO

EXEC dbo.uspModule_Save N'GRNF-004', N'Approve Profile Changes', 1;
EXEC dbo.uspModule_Save N'GRNF-004', N'E-Stubs', 1;
EXEC dbo.uspModule_Save N'GRNF-004', N'Finance Repository', 1;
EXEC dbo.uspModule_Save N'GRNF-004', N'Leave', 1;
GO

EXEC dbo.uspCompany_Save
    @IsNewCompany = 1,
    @CompanyIdentifier = N'RIVR-005',
    @CompanyName = N'Riverbend Health Group',
    @Address1 = N'19 Wellness Plaza',
    @Address2 = N'Floor 3',
    @City = N'Charlotte',
    @State = N'NC',
    @Zip = N'28202',
    @PhoneNumber = N'704-555-0105',
    @PrimaryContact = N'Chris Morgan',
    @PointOfContactEmail = N'chris.morgan@riverbend.example',
    @TaxId = N'56-7890123',
    @BankName = N'Carolina Business Bank',
    @Form1099 = 1,
    @WithholdingNumber = N'WH-NC-5505',
    @County = N'Mecklenburg';
GO

EXEC dbo.uspModule_Save N'RIVR-005', N'Benefits Portal', 1;
EXEC dbo.uspModule_Save N'RIVR-005', N'Document Box', 1;
EXEC dbo.uspModule_Save N'RIVR-005', N'Name Change', 1;
EXEC dbo.uspModule_Save N'RIVR-005', N'W2 Processing', 1;
GO
