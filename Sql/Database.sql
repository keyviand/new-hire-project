IF DB_ID(N'NewHireCompanyManager') IS NULL
BEGIN
    CREATE DATABASE NewHireCompanyManager;
END
GO

USE NewHireCompanyManager;
GO

IF OBJECT_ID(N'dbo.uspModule_Save', N'P') IS NOT NULL DROP PROCEDURE dbo.uspModule_Save;
IF OBJECT_ID(N'dbo.uspModules_DeleteByCompany', N'P') IS NOT NULL DROP PROCEDURE dbo.uspModules_DeleteByCompany;
IF OBJECT_ID(N'dbo.uspLogo_Save', N'P') IS NOT NULL DROP PROCEDURE dbo.uspLogo_Save;
IF OBJECT_ID(N'dbo.uspCompany_Delete', N'P') IS NOT NULL DROP PROCEDURE dbo.uspCompany_Delete;
IF OBJECT_ID(N'dbo.uspCompany_Save', N'P') IS NOT NULL DROP PROCEDURE dbo.uspCompany_Save;
IF OBJECT_ID(N'dbo.uspCompany_Get', N'P') IS NOT NULL DROP PROCEDURE dbo.uspCompany_Get;
IF OBJECT_ID(N'dbo.uspCompany_List', N'P') IS NOT NULL DROP PROCEDURE dbo.uspCompany_List;
GO

IF OBJECT_ID(N'dbo.tblModules', N'U') IS NOT NULL DROP TABLE dbo.tblModules;
IF OBJECT_ID(N'dbo.tblLogos', N'U') IS NOT NULL DROP TABLE dbo.tblLogos;
IF OBJECT_ID(N'dbo.tblCompany', N'U') IS NOT NULL DROP TABLE dbo.tblCompany;
GO

CREATE TABLE dbo.tblCompany
(
    CompanyIdentifier NVARCHAR(50) NOT NULL CONSTRAINT PK_tblCompany PRIMARY KEY,
    CompanyName NVARCHAR(150) NOT NULL,
    Address1 NVARCHAR(150) NULL,
    Address2 NVARCHAR(150) NULL,
    City NVARCHAR(80) NULL,
    State NVARCHAR(2) NULL,
    Zip NVARCHAR(15) NULL,
    PhoneNumber NVARCHAR(25) NULL,
    PrimaryContact NVARCHAR(150) NOT NULL,
    PointOfContactEmail NVARCHAR(150) NOT NULL,
    TaxId NVARCHAR(25) NOT NULL,
    BankName NVARCHAR(150) NOT NULL,
    Form1099 BIT NOT NULL CONSTRAINT DF_tblCompany_Form1099 DEFAULT (0),
    WithholdingNumber NVARCHAR(50) NULL,
    County NVARCHAR(80) NULL,
    CreatedDate DATETIME2 NOT NULL CONSTRAINT DF_tblCompany_CreatedDate DEFAULT (SYSUTCDATETIME()),
    ModifiedDate DATETIME2 NOT NULL CONSTRAINT DF_tblCompany_ModifiedDate DEFAULT (SYSUTCDATETIME())
);
GO

CREATE TABLE dbo.tblLogos
(
    LogoId INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_tblLogos PRIMARY KEY,
    CompanyIdentifier NVARCHAR(50) NOT NULL,
    FileName NVARCHAR(255) NOT NULL,
    ContentType NVARCHAR(100) NOT NULL,
    LogoData VARBINARY(MAX) NOT NULL,
    UploadedDate DATETIME2 NOT NULL CONSTRAINT DF_tblLogos_UploadedDate DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT FK_tblLogos_tblCompany FOREIGN KEY (CompanyIdentifier)
        REFERENCES dbo.tblCompany (CompanyIdentifier) ON DELETE CASCADE
);
GO

CREATE TABLE dbo.tblModules
(
    ModuleId INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_tblModules PRIMARY KEY,
    CompanyIdentifier NVARCHAR(50) NOT NULL,
    ModuleName NVARCHAR(100) NOT NULL,
    IsEnabled BIT NOT NULL CONSTRAINT DF_tblModules_IsEnabled DEFAULT (0),
    CONSTRAINT FK_tblModules_tblCompany FOREIGN KEY (CompanyIdentifier)
        REFERENCES dbo.tblCompany (CompanyIdentifier) ON DELETE CASCADE
);
GO

CREATE INDEX IX_tblModules_CompanyIdentifier ON dbo.tblModules (CompanyIdentifier);
CREATE INDEX IX_tblLogos_CompanyIdentifier ON dbo.tblLogos (CompanyIdentifier);
GO

CREATE PROCEDURE dbo.uspCompany_List
AS
BEGIN
    SET NOCOUNT ON;

    SELECT CompanyIdentifier, CompanyName
    FROM dbo.tblCompany
    ORDER BY CompanyName;
END
GO

CREATE PROCEDURE dbo.uspCompany_Get
    @CompanyIdentifier NVARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        c.CompanyIdentifier,
        c.CompanyName,
        c.Address1,
        c.Address2,
        c.City,
        c.State,
        c.Zip,
        c.PhoneNumber,
        c.PrimaryContact,
        c.PointOfContactEmail,
        c.TaxId,
        c.BankName,
        c.Form1099,
        c.WithholdingNumber,
        c.County,
        l.FileName AS LogoFileName,
        l.ContentType AS LogoContentType
    FROM dbo.tblCompany c
    OUTER APPLY
    (
        SELECT TOP (1) FileName, ContentType
        FROM dbo.tblLogos
        WHERE CompanyIdentifier = c.CompanyIdentifier
        ORDER BY UploadedDate DESC, LogoId DESC
    ) l
    WHERE c.CompanyIdentifier = @CompanyIdentifier;

    SELECT ModuleName, IsEnabled
    FROM dbo.tblModules
    WHERE CompanyIdentifier = @CompanyIdentifier
    ORDER BY ModuleName;
END
GO

CREATE PROCEDURE dbo.uspCompany_Save
    @IsNewCompany BIT,
    @CompanyIdentifier NVARCHAR(50),
    @CompanyName NVARCHAR(150),
    @Address1 NVARCHAR(150) = NULL,
    @Address2 NVARCHAR(150) = NULL,
    @City NVARCHAR(80) = NULL,
    @State NVARCHAR(2) = NULL,
    @Zip NVARCHAR(15) = NULL,
    @PhoneNumber NVARCHAR(25) = NULL,
    @PrimaryContact NVARCHAR(150),
    @PointOfContactEmail NVARCHAR(150),
    @TaxId NVARCHAR(25),
    @BankName NVARCHAR(150),
    @Form1099 BIT,
    @WithholdingNumber NVARCHAR(50) = NULL,
    @County NVARCHAR(80) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    IF @IsNewCompany = 1
    BEGIN
        INSERT INTO dbo.tblCompany
        (
            CompanyIdentifier,
            CompanyName,
            Address1,
            Address2,
            City,
            State,
            Zip,
            PhoneNumber,
            PrimaryContact,
            PointOfContactEmail,
            TaxId,
            BankName,
            Form1099,
            WithholdingNumber,
            County
        )
        VALUES
        (
            @CompanyIdentifier,
            @CompanyName,
            @Address1,
            @Address2,
            @City,
            @State,
            @Zip,
            @PhoneNumber,
            @PrimaryContact,
            @PointOfContactEmail,
            @TaxId,
            @BankName,
            @Form1099,
            @WithholdingNumber,
            @County
        );
    END
    ELSE
    BEGIN
        UPDATE dbo.tblCompany
        SET
            CompanyName = @CompanyName,
            Address1 = @Address1,
            Address2 = @Address2,
            City = @City,
            State = @State,
            Zip = @Zip,
            PhoneNumber = @PhoneNumber,
            PrimaryContact = @PrimaryContact,
            PointOfContactEmail = @PointOfContactEmail,
            TaxId = @TaxId,
            BankName = @BankName,
            Form1099 = @Form1099,
            WithholdingNumber = @WithholdingNumber,
            County = @County,
            ModifiedDate = SYSUTCDATETIME()
        WHERE CompanyIdentifier = @CompanyIdentifier;
    END
END
GO

CREATE PROCEDURE dbo.uspCompany_Delete
    @CompanyIdentifier NVARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;

    DELETE FROM dbo.tblCompany
    WHERE CompanyIdentifier = @CompanyIdentifier;
END
GO

CREATE PROCEDURE dbo.uspLogo_Save
    @CompanyIdentifier NVARCHAR(50),
    @FileName NVARCHAR(255),
    @ContentType NVARCHAR(100),
    @LogoData VARBINARY(MAX)
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO dbo.tblLogos (CompanyIdentifier, FileName, ContentType, LogoData)
    VALUES (@CompanyIdentifier, @FileName, @ContentType, @LogoData);
END
GO

CREATE PROCEDURE dbo.uspModules_DeleteByCompany
    @CompanyIdentifier NVARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;

    DELETE FROM dbo.tblModules
    WHERE CompanyIdentifier = @CompanyIdentifier;
END
GO

CREATE PROCEDURE dbo.uspModule_Save
    @CompanyIdentifier NVARCHAR(50),
    @ModuleName NVARCHAR(100),
    @IsEnabled BIT
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO dbo.tblModules (CompanyIdentifier, ModuleName, IsEnabled)
    VALUES (@CompanyIdentifier, @ModuleName, @IsEnabled);
END
GO
